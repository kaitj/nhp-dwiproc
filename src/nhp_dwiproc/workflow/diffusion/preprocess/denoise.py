"""Preprocess workflow steps associated with denoising."""

from functools import partial
from logging import Logger
from pathlib import Path

import numpy as np
from niwrap import mrtrix
from styxdefs import OutputPathType

import nhp_dwiproc.utils as utils


def denoise(
    nii: Path,
    bval: Path,
    estimator: str | None,
    noise_map: str | None,
    extent: list[int] | None,
    skip: bool = False,
    logger: Logger = Logger(name="logger"),
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
    output_fpath: Path = Path.cwd(),
    **kwargs,
) -> OutputPathType:
    """Perform mrtrix denoising."""
    bval_arr = np.loadtxt(bval)
    if bval_arr[bval_arr != 0].size < 30:
        logger.info("Less than 30 directions...skipping denoising")
        skip = True

    if skip:
        return nii

    logger.info("Performing denoising")
    bids = partial(bids, datatype="dwi")
    denoise = mrtrix.dwidenoise(
        dwi=nii,
        out=bids(desc="denoise", suffix="dwi", ext=".nii.gz"),
        estimator=estimator,
        noise=bids(algorithm=estimator, param="noise", suffix="dwimap", ext=".nii.gz")
        if noise_map
        else None,
        extent=extent,
    )
    if noise_map:
        if not denoise.noise:
            raise ValueError("Noise map was not generated")
        utils.io.save(files=denoise.noise, out_dir=output_fpath)

    return denoise.out
