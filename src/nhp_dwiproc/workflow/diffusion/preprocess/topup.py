"""Preprocess steps associated with FSL's topup."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

from niwrap import fsl
from styxdefs import OutputPathType

from nhp_dwiproc.app import utils


def run_apply_topup(
    b0: pl.Path,
    phenc: pl.Path,
    dwis: list[OutputPathType],
    indices: list[str],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> None:
    """Perform FSL's topup."""
    bids = partial(
        utils.bids_name, datatype="dwi", desc="topup", ext=".nii.gz", **input_group
    )
    logger.info("Running FSL's topup")
    topup = fsl.topup(
        imain=b0,
        datain=phenc,
        config=cfg["participant.preprocess.topup.config"],
        out=bids(ext=None),
        iout=bids(suffix="b0s"),
        fout=bids(suffix="fmap"),
    )

    apply_topup = fsl.applytopup(
        datain=phenc,
        imain=dwis,
        inindex=indices,
        topup="".join(word for word in str(topup.movpar).split("_")[:-1]),
        method=cfg["participant.preprocess.topup.method"],
        out=bids(suffix="topup"),
    )
