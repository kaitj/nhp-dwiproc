"""Preprocess steps associated with FSL's eddy."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

from niwrap import fsl, mrtrix
from styxdefs import InputPathType, OutputPathType

from nhp_dwiproc.app import utils
from nhp_dwiproc.workflow.diffusion.preprocess.dwi import gen_eddy_inputs


def run_eddy(
    phenc: pl.Path,
    topup: fsl.TopupOutputs | None,
    mask_input: InputPathType,
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[OutputPathType, pl.Path, pl.Path]:
    """Perform FSL's eddy."""
    logger.info("Running FSL's eddy")
    if cfg["participant.preprocess.eddy.gpu"]:
        logger.warning("eddy_gpu not yet integrated into workflow...using cpu")

    bids = partial(utils.bids_name, datatype="dwi", ext=".nii.gz", **input_group)
    dwi, bval, bvec, indices = gen_eddy_inputs(
        dir_outs=dir_outs,
        input_group=input_group,
        **kwargs,
    )

    mask = mrtrix.dwi2mask(
        input_=mask_input,
        output=bids(desc="preEddy", suffix="mask"),
        fslgrad=mrtrix.Dwi2maskFslgrad(bvecs=bvec, bvals=bval),
        nthreads=cfg["opt.threads"],
    )

    bids = partial(utils.bids_name, datatype="dwi", desc="eddy_", **input_group)
    eddy = fsl.eddy(
        imain=dwi,
        mask=mask.output,
        bvecs=bvec,
        bvals=bval,
        acqp=phenc,
        index=indices,
        topup=(
            "".join(word for word in str(topup.movpar).split("_")[:-1])
            if topup
            else None
        ),
        out=bids(),
        implementation="_openmp",
    )

    return eddy.out, bval, bvec
