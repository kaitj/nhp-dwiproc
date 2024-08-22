"""Sub-module associated with processing dwi images (e.g. split, concat, etc)."""

from logging import Logger
from typing import Any

import numpy as np
from niwrap import mrtrix
from styxdefs import InputPathType, OutputPathType

from nhp_dwiproc.app import utils
from nhp_dwiproc.lib.dwi import generate_phenc_txt


def get_phenc_data(
    dwi: InputPathType,
    idx: int,
    entities: dict[str, Any],
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[OutputPathType, np.ndarray]:
    """Generate phase-encoding direction data for downstream steps."""
    logger.info("Getting phase-encoding information")
    dwi_b0 = mrtrix.dwiextract(
        input_=dwi,
        output=utils.bids_name(datatype="dwi", suffix="b0", ext=".nii.gz", **entities),
        bzero=True,
        fslgrad=mrtrix.DwiextractFslgrad(
            bvals=input_data["dwi"]["bval"],
            bvecs=input_data["dwi"]["bvec"],
        ),
        nthreads=cfg["opt.threads"],
    )

    pe_data = generate_phenc_txt(
        b0=dwi_b0.output,
        idx=idx,
        input_data=input_data,
        cfg=cfg,
        logger=logger,
    )

    return dwi_b0.output, pe_data
