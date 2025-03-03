"""Preprocess steps associated with FSL's topup."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

from niwrap import fsl

import nhp_dwiproc.utils as utils
from nhp_dwiproc.workflow.diffusion.preprocess.dwi import gen_topup_inputs


def run_apply_topup(
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[pl.Path, list[str], fsl.TopupOutputs]:
    """Perform FSL's topup."""
    bids = partial(
        utils.io.bids_name, datatype="dwi", desc="topup", ext=".nii.gz", **input_group
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
    )
    if not topup.iout:
        raise ValueError("Unable to unwarp b0")

    return phenc, indices, topup
