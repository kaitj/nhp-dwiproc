"""Preprocess workflow steps associated with unringing."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix
from styxdefs import InputPathType, OutputPathType

from nhp_dwiproc.app import utils


def degibbs(
    dwi: InputPathType,
    entities: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> OutputPathType:
    """Minimize Gibbs ringing."""
    bids = partial(
        utils.bids_name(
            datatype="dwi",
            **entities,
        )
    )
    if cfg["participant.preprocess.unring.skip"]:
        return OutputPathType(dwi)

    logger.info("Performing Gibbs unringing")

    degibbs = mrtrix.mrdegibbs(
        in_=dwi,
        out=bids(
            desc="unring",
            suffix="dwi",
            ext=".nii.gz",
        ),
        axes=cfg["participant.preprocess.unring.axes"],
        nshifts=cfg["participant.preprocess.unring.nshifts"],
        min_w=cfg["participant.preprocess.unring.minW"],
        max_w=cfg["participant.preprocess.unring.maxW"],
        nthreads=cfg["opt.threads"],
    )

    return degibbs.out
