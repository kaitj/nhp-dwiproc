"""Preprocessing steps associated with registering to subject's T1w.

NOTE: transforms saved in `anat` folder (similar to fmriprep)
"""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

from niwrap import ants, c3d, fsl, greedy, mrtrix
from styxdefs import InputPathType, OutputPathType

import nhp_dwiproc.utils as utils
from nhp_dwiproc.lib.anat import fake_t2w
from nhp_dwiproc.lib.dwi import rotate_bvec
from nhp_dwiproc.utils.assets import load_nifti


def register(
    dwi: InputPathType,
    bval: InputPathType,
    bvec: InputPathType,
    mask: InputPathType,
    input_group: dict[str, Any],
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[pl.Path, dict[str, Any]]:
    """Rigidly register to T1w with original dwi resolution."""
    logger.info("Computing rigid transformation to structural T1w")
    bids = partial(utils.io.bids_name, datatype="dwi", **input_group)
    b0 = mrtrix.dwiextract(
        input_=dwi,
        output=bids(suffix="b0", ext=".mif"),
        fslgrad=mrtrix.dwiextract_fslgrad_params(bvecs=bvec, bvals=bval),
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
        operations=[fsl.fslmaths_operation_params(mas=mask)],
        output=bids(desc="avgBrain", suffix="b0", ext=".nii.gz"),
    )

    # Fake T2w contrast for registration
    logger.info("Generating fake T2w brain from T1w.")
    t2w = fake_t2w(t1w=input_data["t1w"]["nii"], input_group=input_group, cfg=cfg)
    t2w_brain = fsl.fslmaths(
        input_files=[t2w],
        operations=[fsl.fslmaths_operation_params(mas=input_data["dwi"].get("mask"))],
        output=bids(desc="fakeBrain", suffix="T2w", ext=".nii.gz"),
    )

    # Perform registration
    b0_to_t2 = greedy.greedy_(
        input_images=greedy.greedy_input_images_params(
            fixed=t2w_brain.output_file, moving=b0_brain.output_file
        ),
        output=bids(
            datatype="anat",
            from_="dwi",
            to="T1w",
            method="ras",
            desc="registration",
            suffix="affine",
            ext=".txt",
        ).replace("from_", "from"),
        affine=True,
        affine_dof=6,
        ia_identity=cfg["participant.preprocess.register.init"] == "identity",
        ia_image_centers=cfg["participant.preprocess.register.init"] == "image-centers",
        iterations=cfg["participant.preprocess.register.iters"],
        metric=greedy.greedy_metric_params(
            cfg["participant.preprocess.register.metric"]
        ),
        dimensions=3,
        threads=cfg["opt.threads"],
    )
    transforms = {"ras": b0_to_t2.output_file}
    if not transforms.get("ras"):
        raise ValueError("No RAS transformation found")
    b0_resliced = greedy.greedy_(
        fixed_reslicing_image=t2w,
        reslice_moving_image=greedy.greedy_reslice_moving_image_params(
            moving=b0.output,
            output=bids(space="T1w", desc="avg", suffix="b0", ext=".nii.gz"),
        ),
        reslice=[transforms["ras"]],  # type: ignore
        dimensions=3,
        threads=cfg["opt.threads"],
    )
    if not b0_resliced.reslice_moving_image:
        raise ValueError("b0 image was unable to be resliced.")

    # Create reference in original resolution
    im = load_nifti(b0.output)
    res = "x".join([str(vox) for vox in im.header.get_zooms()]) + "mm"
    ref_b0 = c3d.c3d_(
        input_=[b0_resliced.reslice_moving_image.resliced_image],
        operations=[c3d.c3d_resample_mm_params(res)],
        output=(
            b0_fname := bids(
                space="T1w", res="dwi", desc="ref", suffix="b0", ext=".nii.gz"
            )
        ),
    )

    ras_to_itk = c3d.c3d_affine_tool(
        transform_file=transforms["ras"],
        out_itk_transform=bids(
            datatype="anat",
            from_="dwi",
            to="T1w",
            method="itk",
            desc="registration",
            suffix="affine",
            ext=".mat",
        ).replace("from_", "from"),
    )
    transforms["itk"] = ras_to_itk.itk_transform_outfile

    utils.io.save(
        files=[
            pl.Path(b0_resliced.reslice_moving_image.resliced_image),
            (ref_b0 := (pl.Path(ref_b0.root) / b0_fname)),
            *transforms.values(),  # type: ignore
        ],
        out_dir=cfg["output_dir"] / bids(directory=True),
    )

    return ref_b0, transforms


def apply_transform(
    dwi: InputPathType,
    bvec: InputPathType,
    ref_b0: InputPathType,
    mask: InputPathType,
    transforms: dict[str, Any],
    input_group: dict[str, Any],
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[OutputPathType, OutputPathType, pl.Path]:
    """Apply transform to dwi volume."""
    logger.info("Applying transformations to DWI")
    bids = partial(utils.io.bids_name, datatype="dwi", ext=".nii.gz", **input_group)
    xfm_dwi = ants.ants_apply_transforms(
        dimensionality=3,
        input_image_type=3,
        input_image=dwi,
        reference_image=ref_b0,
        transform=[
            ants.ants_apply_transforms_transform_file_name_params(transforms["itk"])
        ],
        interpolation=ants.ants_apply_transforms_linear_params(),
        output=ants.ants_apply_transforms_warped_output_params(
            bids(space="T1w", res="dwi", desc="preproc", suffix="dwi")
        ),
    )
    xfm_mask = ants.ants_apply_transforms(
        dimensionality=3,
        input_image_type=0,
        input_image=input_data["dwi"].get("mask") or mask,
        reference_image=ref_b0,
        transform=None
        if input_data["dwi"].get("mask")
        else [ants.ants_apply_transforms_transform_file_name_params(transforms["itk"])],
        interpolation=ants.ants_apply_transforms_nearest_neighbor_params(),
        output=ants.ants_apply_transforms_warped_output_params(
            bids(space="T1w", res="dwi", desc="preproc", suffix="mask")
        ),
    )
    xfm_bvec = rotate_bvec(
        bvec_file=pl.Path(bvec),
        transformation=transforms["ras"],
        cfg=cfg,
        input_group=input_group,
        **kwargs,
    )

    utils.io.save(
        files=[
            xfm_dwi.output.output_image_outfile,
            xfm_mask.output.output_image_outfile,
        ],
        out_dir=cfg["output_dir"] / bids(directory=True),
    )

    return (
        xfm_dwi.output.output_image_outfile,
        xfm_mask.output.output_image_outfile,
        xfm_bvec,
    )
