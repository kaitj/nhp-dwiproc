"""Sub-module associated with processing dwi images (e.g. split, concat, etc)."""

from logging import Logger
from typing import Any

from niwrap import mrtrix
from styxdefs import InputPathType, OutputPathType

from nhp_dwiproc.app import utils


def extract_shell(
    dwi: InputPathType,
    shell: int,
    entities: dict[str, Any],
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> OutputPathType:
    """Extract specified shell."""
    bzero = True if shell < cfg["participant.b0_thresh"] else False

    logger.info(f"Extracting shell b={shell}")
    dwi_shell = mrtrix.dwiextract(
        input_=dwi,
        output=utils.bids_name(  # FIX NAME TO BIDS
            datatype="dwi", shell=0, suffix="dwi", ext=".nii.gz", **entities
        ),
        bzero=bzero,
        singleshell=not bzero,
        shells=[shell] if not bzero else None,
        fslgrad=mrtrix.DwiextractFslgrad(
            bvals=input_data["dwi"]["bval"],
            bvecs=input_data["dwi"]["bvec"],
        ),
        nthreads=cfg["opt.threads"],
    )

    return dwi_shell.output
