"""Preprocessing steps associated with registering to subject's T1w.

NOTE: transforms saved in `anat` folder (similar to fmriprep)
"""

from functools import partial
from logging import Logger
from pathlib import Path
from typing import Any

import nibabel.nifti1 as nib
import niwrap_helper
from niwrap import ants, c3d, fsl, greedy, mrtrix

from nhp_dwiproc import config as cfg
from nhp_dwiproc.app.lib.anat import fake_t2w
from nhp_dwiproc.app.lib.dwi import rotate_bvec


def register(
    t1w: Path,
    t1w_mask: Path | None,
    dwi: Path,
    bval: Path,
    bvec: Path,
    mask: Path,
    reg_opts: cfg.preprocess.RegistrationConfig = cfg.preprocess.RegistrationConfig(),
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
    working_dir: Path = Path.cwd() / "tmp",
    output_dir: Path = Path.cwd(),
    logger: Logger = Logger(name=__name__),
    threads: int = 1,
) -> tuple[Path, dict[str, Any]]:
    """Rigidly register to T1w with original dwi resolution.

    Args:
        t1w: Path to T1w nifti.
        t1w_mask: Path to T1w-associated binary mask.
        dwi: Path to diffusion nifti.
        bval: Path to diffusion-associated bval.
        bvec: Path to diffusion-associated bvec.
        mask: Path to diffusion-associated binary mask.
        reg_opts: Registration options.
        reg_method: Registration method to perform.
        iters: Number of iterations.
        metric: Registration metric to use.
        bids: Function to generate BIDS file path.
        working_dir: Working directory for intermediate files.
        output_dir: Output directory to save data to.
        logger: Logger object.
        threads: Number of threads to use in processing.

    Returns:
        A 2-tuple, with a reference transformed b0 and a dictionary of transforms for
        different tools.
    """
    logger.info("Computing rigid transformation to structural T1w")
    b0 = mrtrix.dwiextract(
        input_=dwi,
        output=bids(suffix="b0", ext=".mif"),
        fslgrad={"bvecs": bvec, "bvals": bval},
        bzero=True,
    )
    b0 = mrtrix.mrmath(
        input_=[b0.output],
        output=bids(desc="avg", suffix="b0", ext=".nii.gz"),
        operation="mean",
        axis=3,
    )
    b0_brain = fsl.fslmaths(
        input_files=[b0.output],
        operations=[{"mas": mask}],
        output=bids(desc="avgBrain", suffix="b0", ext=".nii.gz"),
    )
    # Fake T2w contrast for registration
    logger.info("Generating fake T2w brain from T1w.")
    t2w_brain = fake_t2w(t1w=t1w, bids=bids, output_dir=working_dir)
    if t1w_mask:
        t2w_brain = fsl.fslmaths(
            input_files=[t2w_brain],
            operations=[fsl.fslmaths_operation(mas=t1w_mask)],
            output=bids(desc="fakeBrain", suffix="T2w", ext=".nii.gz"),
        ).output_file
    # Perform registration
    b0_to_t2 = greedy.greedy_(
        input_images=greedy.greedy_input_images(
            fixed=t2w_brain, moving=b0_brain.output_file
        ),
        output=bids(
            from_="dwi",
            to="T1w",
            method="ras",
            desc="registration",
            suffix="affine",
            ext=".txt",
        ).replace("from_", "from"),
        affine=True,
        affine_dof=6,
        ia_identity=reg_opts.init == "identity",
        ia_image_centers=reg_opts.init == "image-centers",
        iterations=reg_opts.iters,
        metric={"metric_type": reg_opts.metric},
        dimensions=3,
        threads=threads,
    )
    transforms = {"ras": b0_to_t2.output_file}
    if not transforms.get("ras"):
        raise ValueError("No RAS transformation found")
    b0_resliced = greedy.greedy_(
        fixed_reslicing_image=t2w_brain,
        reslice_moving_image={
            "moving": b0.output,
            "output": bids(space="T1w", desc="avg", suffix="b0", ext=".nii.gz"),
        },
        reslice=[transforms["ras"]],  # type: ignore
        dimensions=3,
        threads=threads,
    )
    if not b0_resliced.reslice_moving_image:
        raise ValueError("b0 image was unable to be resliced.")
    # Create reference in original resolution
    im = nib.load(b0.output)
    res = "x".join([str(vox) for vox in im.header.get_zooms()]) + "mm"
    ref_b0 = c3d.c3d_(
        input_=[b0_resliced.reslice_moving_image.resliced_image],
        operations=[c3d.c3d_resample_mm(res)],
        output=(
            b0_fname := bids(
                space="T1w", res="dwi", desc="ref", suffix="b0", ext=".nii.gz"
            )
        ),
    )
    ras_to_itk = c3d.c3d_affine_tool(
        transform_file=transforms["ras"],
        out_itk_transform=bids(
            from_="dwi",
            to="T1w",
            method="itk",
            desc="registration",
            suffix="affine",
            ext=".mat",
        ).replace("from_", "from"),
    )
    transforms["itk"] = ras_to_itk.itk_transform_outfile
    niwrap_helper.save(
        files=[
            Path(b0_resliced.reslice_moving_image.resliced_image),
            (ref_b0 := (Path(ref_b0.root) / b0_fname)),
            *transforms.values(),  # type: ignore
        ],
        out_dir=output_dir,
    )

    return ref_b0, transforms


def apply_transform(
    dwi: Path,
    bvec: Path,
    ref_b0: Path,
    t1w_mask: Path | None,
    mask: Path,
    transforms: dict[str, Any],
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
    working_dir: Path = Path.cwd() / "tmp",
    output_dir: Path = Path.cwd(),
    logger: Logger = Logger(name=__name__),
) -> tuple[Path, ...]:
    """Apply transform to dwi volume."""
    logger.info("Applying transformations to DWI")
    xfm_dwi = ants.ants_apply_transforms(
        dimensionality=3,
        input_image_type=3,
        input_image=dwi,
        reference_image=ref_b0,
        transform=[ants.ants_apply_transforms_transform_file_name(transforms["itk"])],
        interpolation=ants.ants_apply_transforms_linear(),
        output=ants.ants_apply_transforms_warped_output(
            bids(space="T1w", res="dwi", desc="preproc", suffix="dwi", ext=".nii.gz")
        ),
    )
    xfm_mask = ants.ants_apply_transforms(
        dimensionality=3,
        input_image_type=0,
        input_image=t1w_mask or mask,
        reference_image=ref_b0,
        transform=None
        if t1w_mask
        else [ants.ants_apply_transforms_transform_file_name(transforms["itk"])],
        interpolation=ants.ants_apply_transforms_nearest_neighbor(),
        output=ants.ants_apply_transforms_warped_output(
            bids(space="T1w", res="dwi", desc="preproc", suffix="mask", ext=".nii.gz")
        ),
    )
    xfm_bvec = rotate_bvec(
        bvec_file=Path(bvec),
        transformation=transforms["ras"],
        bids=bids,
        output_dir=working_dir,
    )

    niwrap_helper.save(
        files=[
            xfm_dwi.output.output_image_outfile,
            xfm_mask.output.output_image_outfile,
        ],
        out_dir=output_dir,
    )

    return (
        xfm_dwi.output.output_image_outfile,
        xfm_mask.output.output_image_outfile,
        xfm_bvec,
    )
