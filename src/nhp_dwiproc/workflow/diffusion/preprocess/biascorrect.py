"""Preprocess steps associated with bias correction."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix
from styxdefs import InputPathType, OutputPathType

from nhp_dwiproc.app import utils


def biascorrect(
    dwi: InputPathType,
    bval: pl.Path,
    bvec: pl.Path,
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> OutputPathType:
    """Perform biascorrection steps."""
    logger.info("Performing biascorrection")
    bids = partial(utils.bids_name, datatype="dwi", ext=".nii.gz", **input_group)

    # Fslgrad to be fixed
    biascorrect = mrtrix.dwibiascorrect(
        input_image=dwi,
        output_image=bids(desc="biascorrect", suffix="dwi"),
        algorithm="ants",
        fslgrad=mrtrix.DwibiascorrectFslgrad(
            bvecs=bvec,
            bvals=bval,
        ),
        ants_b=f"{cfg['participant.preprocess.biascorrect.spacing']},3",
        ants_c=f"{cfg['participant.preprocess.biascorrect.iters']},0.0",
        ants_s=f"{cfg['participant.preprocess.biascorrect.shrink']}",
        nthreads=cfg["opt.threads"],
    )
    biascorrect = mrtrix.dwibiascorrect(
        input_image=biascorrect.out,
        output_image=bids(desc="biascorrect", suffix="dwi"),
        algorithm="ants",
        fslgrad=mrtrix.DwibiascorrectFslgrad(
            bvecs=bvec,
            bvals=bval,
        ),
        ants_b=f"{cfg['participant.preprocess.biascorrect.spacing']},3",
        ants_c=f"{cfg['participant.preprocess.biascorrect.iters']},0.0",
        ants_s=f"{cfg['participant.preprocess.biascorrect.shrink']}",
        nthreads=cfg["opt.threads"],
    )

    mrtrix.dwi2mask(
        input_=biascorrect.out,
        output=bids(desc="biascorrect", suffix="mask"),
        fslgrad=mrtrix.Dwi2maskFslgrad(bvecs=bvec, bvals=bval),
        nthreads=cfg["opt.threads"],
    )

    utils.io.save(
        files=biascorrect.out, out_dir=cfg["output_dir"].joinpath(bids(directory=True))
    )

    return biascorrect.output
