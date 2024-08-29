"""Preprocessing steps associated with registering to subject's T1w."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

import nibabel as nib
from niwrap import ants, c3d, mrtrix
from styxdefs import InputPathType, OutputPathType

from nhp_dwiproc.app import utils
from nhp_dwiproc.lib.dwi import rotate_bvec


def register(
    dwi: InputPathType,
    bval: InputPathType,
    bvec: InputPathType,
    input_group: dict[str, Any],
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[pl.Path, OutputPathType]:
    """Rigidly register to T1w with original dwi resolution."""
    logger.info("Computing rigid transformation to structural T1w")
    bids = partial(utils.bids_name, datatype="dwi", **input_group)
    b0 = mrtrix.dwiextract(
        input_=dwi,
        output=bids(suffix="b0", ext=".mif"),
        fslgrad=mrtrix.DwiextractFslgrad(bvecs=bvec, bvals=bval),
        bzero=True,
        nthreads=cfg["opt.threads"],
    )

    b0 = mrtrix.mrmath(
        input_=[b0.output],
        output=bids(desc="avg", suffix="b0", ext=".nii.gz"),
        operation="mean",
        axis=3,
        nthreads=cfg["opt.threads"],
    )

    # Perform registration
    b0_to_t1 = ants.ants_registration_sy_n(
        image_dimension=3,
        fixed_image=input_data["t1w"]["nii"],
        moving_image=b0.output,
        output_prefix=(
            ants_prefix := bids(
                from_="dwi", to="T1w", method="ants_", desc="registration"
            ).replace("from_", "from")
        ),
        transform_type="r",
        initial_transform=[str(input_data["t1w"]["nii"]), str(b0.output), "0"],
        random_seed=cfg["opt.seed_num"],
        threads=cfg["opt.threads"],
    )
    # Create reference in original resolution
    im = nib.loadsave.load(b0.output)
    res = "x".join([str(vox) for vox in im.header.get_zooms()]) + "mm"
    ref_b0 = c3d.c3d(
        input_=b0_to_t1.root / f"{ants_prefix}Warped.nii.gz",
        operations=c3d.C3dResampleMm(res),
        output=(b0_fname := bids(desc="ref", suffix="b0", ext=".nii.gz")),
    )

    # Convert transform to ANTs compatible format
    transform = c3d.c3d_affine_tool(
        reference_file=input_data["t1w"]["nii"],
        source_file=b0.output,
        transform_file=str(b0_to_t1.output_transform).replace("*", "0GenericAffine"),
        ras2fsl=True,
        out_matfile=bids(
            from_="dwi",
            to="T1w",
            method="fsl",
            desc="registration",
            suffix="0GenericAffine",
        ).replace("from_", "from"),
    )

    utils.io.save(
        files=[
            (ref_b0 := pl.Path(ref_b0.root).joinpath(b0_fname)),
            transform.matrix_transform_outfile,
        ],
        out_dir=cfg["output_dir"].joinpath(bids(directory=True)),
    )

    return ref_b0, transform.matrix_transform_outfile


def apply_transform(
    dwi: InputPathType,
    bvec: InputPathType,
    ref_b0: InputPathType,
    mask: InputPathType,
    xfm: InputPathType,
    input_group: dict[str, Any],
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> None:
    """Apply transform to dwi volume."""
    logger.info("Applying transformations to DWI")
    bids = partial(utils.bids_name, datatype="dwi", ext=".nii.gz", **input_group)
    xfm_dwi = ants.ants_apply_transforms(
        dimensionality=3,
        input_image_type=3,
        input_image=dwi,
        reference_image=ref_b0,
        transform=[ants.AntsApplyTransformsTransformFileName(xfm)],
        interpolation=ants.AntsApplyTransformsLinear(),
        output=ants.AntsApplyTransformsWarpedOutput(
            bids(space="T1w", res="dwi", suffix="dwi")
        ),
    )
    xfm_mask = ants.ants_apply_transforms(
        dimensionality=3,
        input_image_type=0,
        input_image=input_data["custom"]["mask"] or mask,
        reference_image=ref_b0,
        transform=[ants.AntsApplyTransformsTransformFileName(xfm)],
        interpolation=ants.AntsApplyTransformsNearestNeighbor(),
        output=ants.AntsApplyTransformsWarpedOutput(
            bids(space="T1w", res="dwi", suffix="mask")
        ),
    )
    xfm_bvec = rotate_bvec(
        bvec_file=pl.Path(bvec),
        transformation=ants.AntsApplyTransformsTransformFileName(xfm),
        **kwargs,
    )

    utils.io.save(
        files=[
            xfm_dwi.output.output_image_outfile,
            xfm_mask.output.output_image_outfile,
            xfm_bvec,
        ],
        out_dir=cfg["output_dir"].joinpath(bids(directory=True)),
    )
