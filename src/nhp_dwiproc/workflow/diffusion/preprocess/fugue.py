"""Preprocess steps associated with FSL's FUGUE.

This step is added to process data collected with prepared fieldmaps.
"""

from functools import partial
from logging import Logger
from pathlib import Path
from typing import Any

import niwrap_helper
from niwrap import fsl

from nhp_dwiproc.lib import metadata

WARP_DIR = {"i": "x", "i-": "x-", "j": "y", "j-": "y-", "k": "z", "k-": "z-"}


def run_fugue(
    dwi: Path,
    fmap: Path,
    pe_dir: str,
    json: dict[str, Any],
    echo_spacing: str | None,
    smooth: float | None,
    logger: Logger = Logger(name="logger"),
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
) -> Path:
    """Perform FSL's FUGUE."""
    logger.info("Running FSL's fugue")
    if pe_dir not in WARP_DIR:
        logger.warning(
            "Unrecognized phase encode direction, using default warp direction 'y'"
        )

    fugue = fsl.fugue(
        in_file=dwi,
        unwarped_file=bids(desc="fugue", ext=".nii.gz"),
        fmap_in_file=fmap,
        dwell_time=metadata.echo_spacing(
            dwi_json=json, echo_spacing=echo_spacing, logger=logger
        ),
        unwarp_direction=WARP_DIR.get(pe_dir, "y"),  # type: ignore
        smooth3d=smooth,
    )

    if not fugue.unwarped_file_outfile:
        raise ValueError("Unable to generate undistorted file with FSL's FUGUE")

    return fugue.unwarped_file_outfile
