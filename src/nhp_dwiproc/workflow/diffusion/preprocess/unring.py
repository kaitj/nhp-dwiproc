"""Preprocess workflow steps associated with unringing."""

from functools import partial
from logging import Logger
from pathlib import Path

import niwrap_helper
from niwrap import mrtrix


def degibbs(
    dwi: Path,
    axes: list[int] | None,
    nshifts: int | None,
    min_w: int | None,
    max_w: int | None,
    skip: bool = False,
    logger: Logger = Logger(name="logger"),
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
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
