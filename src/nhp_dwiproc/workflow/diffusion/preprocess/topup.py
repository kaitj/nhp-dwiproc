"""Preprocess steps associated with FSL's topup."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

from niwrap import fsl, mrtrix

from nhp_dwiproc.app import utils
from nhp_dwiproc.workflow.diffusion.preprocess.dwi import gen_topup_inputs


def run_apply_topup(
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[pl.Path, list[str], fsl.TopupOutputs, mrtrix.Dwi2maskOutputs]:
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
        config=None,  # cfg["participant.preprocess.topup.config"],
        out=f"{bids(ext=None)}",
        iout=bids(suffix="b0s"),
        fout=bids(suffix="fmap"),
        nthr=cfg["opt.threads"],
    )

    apply_topup = fsl.applytopup(
        datain=phenc,
        imain=[str(dwi) for dwi in dir_outs["b0"]],
        inindex=indices,
        topup_dir=f"{topup.movpar.parent}",
        topup=f'{"_".join(word for word in topup.movpar.name.split("_")[:-1])}',
        method=cfg["participant.preprocess.topup.method"],
        out=bids(suffix="dwi"),
    )

    # mask = mrtrix.dwi2mask(
    #     input_=apply_topup.output_file,
    #     output=bids(desc="preEddy", suffix="mask"),
    #     fslgrad=mrtrix.Dwi2maskFslgrad(
    #         bvecs=dir_outs["b0_bvec"][0], bvals=dir_outs["b0_bval"][0]
    #     ),
    #     nthreads=cfg["opt.threads"],
    # )

    # For debugging purposes, use FSL's bet
    # Also need to update eddy mask input
    mask = fsl.bet(
        infile=apply_topup.output_file,
        maskfile=bids(desc="preEddy", suffix="mask", ext=None),
    )

    return phenc, indices, topup, mask
