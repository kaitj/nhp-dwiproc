"""Preprocess workflow steps associated with unringing."""

import logging
from functools import partial
from pathlib import Path

import niwrap_helper
from niwrap import mrtrix

from nhp_dwiproc.config.preprocess import UnringConfig


def degibbs(
    dwi: Path,
    unring_opts: UnringConfig | None = UnringConfig(),
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    **kwargs,
) -> Path:
    """Minimize Gibbs ringing artifacts.

    Args:
        dwi: File path to diffusion nifti
        unring_opts: Unringing configuration options
        bids: Function to generate bids filepath.
        **kwargs: Arbitrary keyword input arguments.

    Returns:
        Nifti file path.

    Raises:
        TypeError: If configuration of unexpected type.
    """
    if not isinstance(unring_opts, UnringConfig):
        raise TypeError(f"Expected UnringConfig, got {type(UnringConfig)}")
    logger = kwargs.get("logger", logging.Logger(__name__))
    if unring_opts.skip:
        logger.info("Skipping Gibbs unringing")
        return dwi

    logger.info("Performing Gibbs unringing")
    degibbs = mrtrix.mrdegibbs(
        in_=dwi,
        out=bids(datatype="dwi", desc="unring", suffix="dwi", ext=".nii.gz"),
        axes=list(unring_opts.axes) if unring_opts.axes is not None else None,
    )
    return degibbs.out
