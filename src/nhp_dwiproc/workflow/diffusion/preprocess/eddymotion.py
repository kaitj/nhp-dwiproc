"""Preprocess steps associated with eddymotion."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

import numpy as np
from eddymotion.data import dmri
from eddymotion.estimator import EddyMotionEstimator

from nhp_dwiproc.app import utils
from nhp_dwiproc.lib.utils import gen_hash


def eddymotion(
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[pl.Path, ...]:
    """Perform eddymotion."""
    bids = partial(
        utils.bids_name, datatype="dwi", desc="eddymotion", ext=".nii.gz", **input_group
    )
    logger.info("Running eddymotion")

    if any(
        (len(dir_outs["dwi"]) > 1, len(dir_outs["bvec"]) > 1, len(dir_outs["bval"]) > 1)
    ):
        raise ValueError("Multiple diffusion-associated files found")

    out_fpath = cfg["opt.working_dir"] / f"{gen_hash()}_eddymotion"
    out_fpath.mkdir(parents=True, exist_ok=True)

    dwi_data = dmri.load(
        filename=dir_outs["dwi"][0],
        bvec_file=dir_outs["bvec"][0],
        bval_file=dir_outs["bval"][0],
    )

    estimator = EddyMotionEstimator()
    estimator.estimate(
        dwi_data,
        models=["b0"],
        n_iter=cfg["participant.preprocess.eddymotion.iters"],
        seed=cfg["opt.seed_num"],
        omp_nthreads=cfg["opt.threads"],
    )

    # Update output directory
    dwi_fpath = out_fpath / bids(suffix="dwi")
    dwi_data.to_nifti(filename=dwi_fpath, insert_b0=True)

    # Update rotated bvecs and save
    zeros = np.zeros((dwi_data.gradients[:3].shape[0], 1))
    bvecs = np.hstack((zeros, dwi_data.gradients[:3]))
    bvecs_fpath = out_fpath / bids(suffix="dwi", ext=".bvec")
    np.savetxt(bvecs_fpath, bvecs, fmt="%.5f")

    return dwi_fpath, dir_outs["bval"][0], bvecs_fpath
