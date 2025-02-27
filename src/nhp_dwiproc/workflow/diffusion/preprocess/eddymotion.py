"""Preprocess steps associated with eddymotion."""

from functools import partial
from pathlib import Path

import numpy as np
from eddymotion.data import dmri
from eddymotion.estimator import EddyMotionEstimator

import nhp_dwiproc.utils as utils


def eddymotion(
    dwi: list[Path],
    bvec: list[Path],
    bval: list[Path],
    iters: int,
    seed: int,
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
    output_dir: Path = Path.cwd() / "tmp",
    threads: int = 1,
    **kwargs,
) -> tuple[Path, ...]:
    """Perform eddymotion."""
    if any((len(dwi) > 1, len(bvec) > 1, len(bval) > 1)):
        raise ValueError("Multiple diffusion-associated files found")

    out_fpath = output_dir / f"{utils.assets.gen_hash()}_eddymotion"
    out_fpath.mkdir(parents=True, exist_ok=True)

    dwi_data = dmri.load(filename=dwi[0], bvec_file=bvec[0], bval_file=bval[0])
    estimator = EddyMotionEstimator()
    estimator.estimate(
        dwdata=dwi_data,
        models=["b0"],
        n_iter=iters,
        seed=seed,
        omp_nthreads=threads,
    )

    # Update output directory
    dwi_fpath = out_fpath / bids(desc="eddymotion", suffix="dwi", ext=".nii.gz")
    dwi_data.to_nifti(filename=dwi_fpath, insert_b0=True)

    # Update rotated bvecs and save
    zeros = np.zeros((dwi_data.gradients[:3].shape[0], 1))
    bvecs = np.hstack((zeros, dwi_data.gradients[:3]))
    bvecs_fpath = out_fpath / bids(suffix="dwi", ext=".bvec")
    np.savetxt(bvecs_fpath, bvecs, fmt="%.5f")

    return dwi_fpath, bval[0], bvecs_fpath
