"""Sub-module associated with processing dwi images (e.g. split, concat, etc)."""

import pathlib as pl
from logging import Logger
from typing import Any

import numpy as np
from niwrap import mrtrix
from styxdefs import InputPathType, OutputPathType

from nhp_dwiproc.app import utils
from nhp_dwiproc.lib.dwi import concat_dir_phenc_data, generate_phenc_txt, normalize


def get_phenc_data(
    dwi: InputPathType,
    idx: int,
    entities: dict[str, Any],
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[OutputPathType, np.ndarray]:
    """Generate phase-encoding direction data for downstream steps."""
    logger.info("Getting phase-encoding information")
    dwi_b0 = mrtrix.dwiextract(
        input_=dwi,
        output=utils.bids_name(datatype="dwi", suffix="b0", ext=".nii.gz", **entities),
        bzero=True,
        fslgrad=mrtrix.DwiextractFslgrad(
            bvals=input_data["dwi"]["bval"],
            bvecs=input_data["dwi"]["bvec"],
        ),
        nthreads=cfg["opt.threads"],
    )

    pe_data = generate_phenc_txt(
        b0=dwi_b0.output,
        idx=idx,
        input_data=input_data,
        cfg=cfg,
        logger=logger,
    )

    return dwi_b0.output, pe_data


def gen_fsl_inputs(
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    **kwargs,
) -> tuple[pl.Path, pl.Path]:
    """Generate concatenated inputs for topup."""
    phenc_fpath = concat_dir_phenc_data(
        pe_data=dir_outs["pe_data"], input_group=input_group, cfg=cfg
    )

    if len(dir_outs["b0"]) > 1:
        dwi_b0 = mrtrix.mrcat(
            image1=dir_outs["b0"][0],
            image2=dir_outs["b0"][1:],
            output=utils.bids_name(
                datatype="dwi", suffix="b0", ext=".nii.gz", **input_group
            ),
            nthreads=cfg["opt.threads"],
        )
        dwi_b0 = dwi_b0.output
    else:
        dwi_b0 = dir_outs["b0"][0]
    dwi_fpath = normalize(dwi_b0, input_group=input_group, cfg=cfg)

    return phenc_fpath, dwi_fpath
