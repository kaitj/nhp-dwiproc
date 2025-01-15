"""Preprocess steps associated with FSL's topup."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

from niwrap import fsl, mrtrix
from styxdefs import OutputPathType

from nhp_dwiproc.app import utils
from nhp_dwiproc.workflow.diffusion.preprocess.dwi import gen_topup_inputs


def run_apply_topup(
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[pl.Path, list[str], fsl.TopupOutputs, OutputPathType]:
    """Perform FSL's topup."""
    bids = partial(
        utils.bids_name, datatype="dwi", desc="topup", ext=".nii.gz", **input_group
    )
    logger.info("Running FSL's topup")

    phenc, b0, indices = gen_topup_inputs(
        dir_outs=dir_outs, input_group=input_group, cfg=cfg, **kwargs
    )

    topup = fsl.topup(
        imain=b0,
        datain=phenc,
        config=cfg["participant.preprocess.topup.config"],
        out=f"{bids(ext=None)}",
        iout=bids(suffix="b0s"),
        fout=bids(suffix="fmap"),
        nthr=cfg["opt.threads"],
    )
    if not topup.iout:
        raise ValueError("Unable to unwarp b0")

    # Generate crude mask for eddy
    mean_topup = mrtrix.mrmath(
        input_=[topup.iout],
        operation="mean",
        output=bids(desc="mean", suffix="b0"),
        axis=3,
    )
    mask = fsl.bet(
        infile=mean_topup.output,
        maskfile=bids(desc="preEddy", suffix="brain", ext=None),
        binary_mask=True,
    )

    return phenc, indices, topup, mask.binary_mask
