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
    phenc: pl.Path | None,
    indices: list[str] | None,
    topup: fsl.TopupOutputs | None,
    mask: InputPathType | None,
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[OutputPathType, pl.Path, pl.Path]:
    """Perform FSL's eddy."""
    bids = partial(utils.bids_name, datatype="dwi", ext=".nii.gz", **input_group)
    dwi, bval, bvec, phenc, index_fpath = gen_eddy_inputs(
        phenc=phenc,
        indices=indices,
        dir_outs=dir_outs,
        input_group=input_group,
        cfg=cfg,
        **kwargs,
    )

    # Generate crude mask for eddy if necessary
    if not mask:
        mask = mrtrix.dwi2mask(
            input_=dwi,
            output=bids(desc="preEddy", suffix="mask"),
            fslgrad=mrtrix.Dwi2maskFslgrad(bvecs=bvec, bvals=bval),
            nthreads=cfg["opt.threads"],
        ).output

    logger.info("Running FSL's eddy")
    if cfg["participant.preprocess.eddy.gpu"]:
        logger.warning("eddy_gpu not yet integrated into workflow...using cpu")
    bids = partial(utils.bids_name, datatype="dwi", desc="eddy", **input_group)
    eddy = fsl.eddy(
        imain=dwi,
        mask=mask,
        bvecs=bvec,
        bvals=bval,
        acqp=phenc,
        index=index_fpath,
        topup_dir=f"{topup.movpar.parent}" if topup else None,
        topup=f'{"_".join(word for word in topup.movpar.name.split("_")[:-1])}'
        if topup
        else None,
        out=bids(),
        slm=cfg.get("participant.preprocess.eddy.slm", None),
        cnr_maps=cfg["participant.preprocess.eddy.cnr_maps"],
        repol=cfg["participant.preprocess.eddy.repol"],
        residuals=cfg["participant.preprocess.eddy.residuals"],
        data_is_shelled=cfg["participant.preprocess.eddy.shelled"],
    )
    bvec_fpath = pl.Path(str(eddy.out).replace(".nii.gz", ".eddy_rotated_bvecs"))

    # TODO: save cnr maps, residuals

    return eddy.out, bval, bvec_fpath
