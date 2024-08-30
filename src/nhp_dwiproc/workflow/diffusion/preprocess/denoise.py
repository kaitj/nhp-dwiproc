"""Preprocess workflow steps associated with denoising."""

from functools import partial
from logging import Logger
from typing import Any

import numpy as np
from niwrap import mrtrix
from styxdefs import OutputPathType

from nhp_dwiproc.app import utils


def denoise(
    entities: dict[str, Any],
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> OutputPathType:
    """Perform mrtrix denoising."""
    bval = np.loadtxt(input_data["dwi"]["bval"])
    if bval[bval != 0].size < 30:
        logger.info("Less than 30 directions...skipping denoising")
        cfg["participant.preprocess.denoise.skip"] = True

    if cfg["participant.preprocess.denoise.skip"]:
        return input_data["dwi"]["nii"]

    logger.info("Performing denoising")
    bids = partial(utils.bids_name, datatype="dwi", **entities)

    denoise = mrtrix.dwidenoise(
        dwi=input_data["dwi"]["nii"],
        out=bids(
            desc="denoise",
            suffix="dwi",
            ext=".nii.gz",
        ),
        estimator=cfg["participant.preprocess.denoise.estimator"],
        noise=bids(
            algorithm=cfg["participant.preprocess.denoise.estimator"],
            param="noise",
            suffix="dwimap",
            ext=".nii.gz",
        )
        if (noise_map := cfg["participant.preprocess.denoise.map"])
        else None,
        extent=cfg.get("participant.preprocess.denoise.extent"),
        nthreads=cfg["opt.threads"],
    )

    if noise_map:
        utils.io.save(
            files=denoise.noise,
            out_dir=cfg["output_dir"].joinpath(bids(directory=True)),
        )

    return denoise.out
