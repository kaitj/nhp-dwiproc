"""Preprocess steps associated with FSL's FUGUE.

This step is added to process data collected with prepared fieldmaps.
"""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import fsl, mrtrix
from styxdefs import OutputPathType

from nhp_dwiproc.app import utils
from nhp_dwiproc.lib import metadata


def run_fugue(
    input_data: dict[str, Any],
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[fsl.FugueOutputs, OutputPathType]:
    """Perform FSL's FUGUE."""
    bids = partial(
        utils.bids_name, datatype="dwi", desc="topup", ext=".nii.gz", **input_group
    )
    logger.info("Running FSL's fugue")

    assert len(dir_outs["dwi"]) == 1

    fugue = fsl.fugue(
        in_file=dir_outs["dwi"][0],
        unwarped_file=bids(desc="fugue"),
        fmap_in_file=input_data["fmap"]["nii"],
        dwell_time=metadata.echo_spacing(
            dwi_json=input_data["dwi"]["json"], cfg=cfg, logger=logger, **kwargs
        ),
    )

    # Generate crude mask for eddy
    mean_fugue = mrtrix.mrmath(
        input_=[fugue.unwarped_file_outfile],
        operation="mean",
        output=bids(desc="mean", suffix="b0"),
        axis=3,
    )
    mask = fsl.bet(
        infile=mean_fugue.output,
        maskfile=bids(desc="preEddy", suffix="brain", ext=None),
        binary_mask=True,
    )

    return fugue, mask.binary_mask
