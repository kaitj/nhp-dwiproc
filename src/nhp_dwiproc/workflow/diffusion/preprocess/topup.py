"""Preprocess steps associated with FSL's topup."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import fsl
from styxdefs import OutputPathType

from nhp_dwiproc.app import utils
from nhp_dwiproc.workflow.diffusion.preprocess.dwi import gen_topup_inputs


def run_apply_topup(
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[fsl.TopupOutputs, OutputPathType]:
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
        out=bids(ext=None),
        iout=bids(suffix="b0s"),
        fout=bids(suffix="fmap"),
        nthr=cfg["opt.threads"],
    )

    apply_topup = fsl.applytopup(
        datain=phenc,
        imain=[str(dwi) for dwi in dir_outs["dwi"]],
        inindex=indices,
        topup=str(
            topup.root
            / f'{"_".join(word for word in str(topup.movpar).split("_")[:-1])}_'
        ),
        method=cfg["participant.preprocess.topup.method"],
        out=bids(suffix="topup"),
    )

    return topup, apply_topup.output_file
