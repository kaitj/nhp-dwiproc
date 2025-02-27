"""Preprocess workflow steps associated with unringing."""

from functools import partial
from logging import Logger
from pathlib import Path

from niwrap import mrtrix

import nhp_dwiproc.utils as utils


def degibbs(
    dwi: Path,
    axes: list[int] | None,
    nshifts: int | None,
    min_w: int | None,
    max_w: int | None,
    skip: bool = False,
    logger: Logger = Logger(name="logger"),
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
) -> Path:
    """Minimize Gibbs ringing."""
    if skip:
        return dwi

    logger.info("Performing Gibbs unringing")
    degibbs = mrtrix.mrdegibbs(
        in_=dwi,
        out=bids(datatype="dwi", desc="unring", suffix="dwi", ext=".nii.gz"),
        axes=axes,
        nshifts=nshifts,
        min_w=min_w,
        max_w=max_w,
    )
    return degibbs.out
