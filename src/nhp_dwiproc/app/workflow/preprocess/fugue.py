"""Preprocess steps associated with FSL's FUGUE.

This step is added to process data collected with prepared fieldmaps.
"""

import logging
from functools import partial
from pathlib import Path
from typing import Any

import niwrap_helper
from niwrap import fsl

from ....config.preprocess import FugueConfig
from ...lib import metadata

WARP_DIR = {"i": "x", "i-": "x-", "j": "y", "j-": "y-", "k": "z", "k-": "z-"}


def run_fugue(
    dwi: Path,
    fmap: Path,
    pe_dir: str,
    json: dict[str, Any],
    echo_spacing: str | None,
    fugue_opts: FugueConfig | None = FugueConfig(),
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
    **kwargs,
) -> Path:
    """Perform FSL's FUGUE.

    Args:
        dwi: Diffusion nifti file path.
        fmap: Field map nifti file path.
        pe_dir: Phase encoding direction.
        json: Associated metadata.
        echo_spacing: Associated echo spacing.
        fugue_opts: Fugue configruation options.
        bids: Function to generate BIDS file path.
        **kwargs: Arbitrary keyword input arguments.

    Returns:
        FUGUE unwarped file path.

    Raises:
        TypeError: Unexpected configuration type.
        ValueError: If unable to generate undistorted file with FUGUE.
    """
    if not isinstance(fugue_opts, FugueConfig):
        raise TypeError(f"Expected FugueConfig, got {type(fugue_opts)}")
    logger = kwargs.get("logger", logging.Logger(__name__))
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
        smooth3d=fugue_opts.smooth,
    )
    if not fugue.unwarped_file_outfile:
        raise ValueError("Unable to generate undistorted file with FSL's FUGUE")
    return fugue.unwarped_file_outfile
