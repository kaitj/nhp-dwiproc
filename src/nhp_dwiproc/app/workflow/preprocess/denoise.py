"""Sub-workflow for denoising during preprocesing stage."""

import logging
from functools import partial
from pathlib import Path

import niwrap_helper
import numpy as np
from niwrap import OutputPathType, mrtrix

from nhp_dwiproc.config.preprocess import DenoiseConfig


def denoise(
    nii: Path,
    bval: Path,
    denoise_opts: DenoiseConfig | None = DenoiseConfig(),
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
    output_fpath: Path = Path.cwd(),
    **kwargs,
) -> OutputPathType:
    """Perform mrtrix denoising.

    Args:
        nii: File path to diffusion nifti.
        bval: File path to diffusion bval.
        denoise_opts: Denoise configuration options.
        bids: Function to generate bids filepath.
        output_fpath: Output directory.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        Nifti filepath

    Raises:
        TypeError: If unexpected configuration type.
        ValueError: If noise map is not generated when expected.
    """
    if not isinstance(denoise_opts, DenoiseConfig):
        raise TypeError(f"Expected DenoiseConfig, got {type(denoise_opts)}")
    logger = kwargs.get("logger", logging.Logger(__name__))

    bval_arr = np.loadtxt(bval)
    if bval_arr[bval_arr != 0].size < 30:
        logger.info("Less than 30 directions...skipping denoising")
        denoise_opts.skip = True
        return nii

    logger.info("Performing denoising")
    bids = partial(bids, datatype="dwi")
    denoise = mrtrix.dwidenoise(
        dwi=nii,
        out=bids(desc="denoise", suffix="dwi", ext=".nii.gz"),
        estimator=denoise_opts.estimator,
        noise=bids(
            algorithm=denoise_opts.estimator,
            param="noise",
            suffix="dwimap",
            ext=".nii.gz",
        )
        if denoise_opts.map_
        else None,
    )
    if denoise_opts.map_:
        if not denoise.noise:
            raise ValueError("Noise map was not generated")
        niwrap_helper.save(files=denoise.noise, out_dir=output_fpath)
    return denoise.out
