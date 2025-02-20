"""Preprocess steps associated with bias correction."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix
from styxdefs import InputPathType, OutputPathType

import nhp_dwiproc.utils as utils


def biascorrect(
    dwi: InputPathType,
    bval: pl.Path,
    bvec: pl.Path,
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[OutputPathType, ...]:
    """Perform biascorrection steps."""
    logger.info("Performing biascorrection")
    bids = partial(utils.io.bids_name, datatype="dwi", ext=".nii.gz", **input_group)

    biascorrect = mrtrix.dwibiascorrect(
        input_image=dwi,
        output_image=bids(desc="biascorrect", suffix="dwi"),
        algorithm="ants",
        fslgrad=mrtrix.dwibiascorrect_fslgrad_params(bvecs=bvec, bvals=bval),
        ants_b=f"{cfg['participant.preprocess.biascorrect.spacing']},3",
        ants_c=f"{cfg['participant.preprocess.biascorrect.iters']},0.0",
        ants_s=f"{cfg['participant.preprocess.biascorrect.shrink']}",
    )
    biascorrect = mrtrix.dwibiascorrect(
        input_image=biascorrect.output_image_file,
        output_image=bids(desc="preproc", suffix="dwi"),
        algorithm="ants",
        fslgrad=mrtrix.dwibiascorrect_fslgrad_params(bvecs=bvec, bvals=bval),
        ants_b=f"{cfg['participant.preprocess.biascorrect.spacing']},3",
        ants_c=f"{cfg['participant.preprocess.biascorrect.iters']},0.0",
        ants_s=f"{cfg['participant.preprocess.biascorrect.shrink']}",
    )

    mask = mrtrix.dwi2mask(
        input_=biascorrect.output_image_file,
        output=bids(desc="biascorrect", suffix="mask"),
        fslgrad=mrtrix.dwi2mask_fslgrad_params(bvecs=bvec, bvals=bval),
    )

    utils.io.save(
        files=biascorrect.output_image_file,
        out_dir=cfg["output_dir"] / bids(directory=True),
    )

    return biascorrect.output_image_file, mask.output
