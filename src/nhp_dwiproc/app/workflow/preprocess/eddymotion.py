"""Preprocess steps associated with eddymotion."""

import logging
from functools import partial
from pathlib import Path

import niwrap_helper
import numpy as np
from eddymotion.data import dmri
from eddymotion.estimator import EddyMotionEstimator

from nhp_dwiproc.config.preprocess import EddyMotionConfig


def eddymotion(
    dwi: list[Path],
    bvec: list[Path],
    bval: list[Path],
    eddymotion_opts: EddyMotionConfig | None = EddyMotionConfig(),
    seed: int = 42,
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: Path = Path.cwd() / "tmp",
    threads: int = 1,
    **kwargs,
) -> tuple[Path, ...]:
    """Perform eddymotion.

    Args:
        dwi: List of diffusion file paths to process.
        bval: List of diffusion associated bval file paths.
        bvec: List of diffusion associated bvec file paths.
        eddymotion_opts: Eddymotion configuration options.
        seed: Seed number to use for reproducible results.
        bids: Function to generate BIDS file path.
        output_dir: Output directory to save files.
        threads: Number of threads to use during processing.
        **kwargs: Arbitrary keyword input arguments.

    Returns:
        A 3-tuple, with the eddymotion-correct diffusion nifti, bval, and rotated-bvec
        file paths.

    Raises:
        ValueError: If multiple diffusion-associated files found and step to be skipped.
    """
    if not isinstance(eddymotion_opts, EddyMotionConfig):
        raise TypeError(f"Expected EddyMotionConfig, got {type(eddymotion_opts)}")
    logger = kwargs.get("logger", logging.Logger(__name__))
    if any((len(dwi) > 1, len(bvec) > 1, len(bval) > 1)):
        raise ValueError("Multiple diffusion-associated files found")

    dwi_file, bvec_file, bval_file = dwi[0], bvec[0], bval[0]
    if eddymotion_opts.skip:
        logger.info("Skipping Eddymotion step.")
        return dwi_file, bval_file, bvec_file

    out_fpath = output_dir / f"{niwrap_helper.gen_hash()}_eddymotion"
    out_fpath.mkdir(parents=True, exist_ok=True)

    dwi_data = dmri.load(filename=dwi_file, bvec_file=bvec_file, bval_file=bval_file)
    estimator = EddyMotionEstimator()
    estimator.estimate(
        dwdata=dwi_data,
        models=["b0"],
        n_iter=eddymotion_opts.iters,
        omp_nthreads=threads,
        seed=seed,
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
