"""Preprocess steps associated with FSL's FUGUE.

This step is added to process data collected with prepared fieldmaps.
"""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import fsl
from styxdefs import InputPathType, OutputPathType

import nhp_dwiproc.utils as utils
from nhp_dwiproc.lib import metadata

WARP_DIR = {"i": "x", "i-": "x-", "j": "y", "j-": "y-", "k": "z", "k-": "z-"}


def run_fugue(
    input_data: dict[str, Any],
    dwi: InputPathType,
    pe_dir: str,
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> OutputPathType:
    """Perform FSL's FUGUE."""
    bids = partial(
        utils.io.bids_name, datatype="dwi", desc="fugue", ext=".nii.gz", **input_group
    )
    logger.info("Running FSL's fugue")

    if pe_dir not in WARP_DIR:
        logger.warning(
            "Unrecognized phase encode direction, using default warp direction 'y'"
        )

    fugue = fsl.fugue(
        in_file=dwi,
        unwarped_file=bids(),
        fmap_in_file=input_data["fmap"]["nii"],
        dwell_time=metadata.echo_spacing(
            dwi_json=input_data["dwi"]["json"], cfg=cfg, logger=logger, **kwargs
        ),
        unwarp_direction=WARP_DIR.get(pe_dir, None),  # type: ignore
        smooth3d=cfg["participant.preprocess.fugue.smooth"],
    )

    if not fugue.unwarped_file_outfile:
        raise ValueError("Unable to generate undistorted file with FSL's FUGUE")

    return fugue.unwarped_file_outfile
