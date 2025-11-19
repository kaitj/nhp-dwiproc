"""Preprocess steps associated with FSL's eddy."""

import logging
from functools import partial
from pathlib import Path

import niwrap_helper
import numpy as np
from niwrap import fsl, mrtrix

from nhp_dwiproc.app.workflow.preprocess.dwi import gen_eddy_inputs
from nhp_dwiproc.config.preprocess import EddyConfig


def run_eddy(
    dwi: list[Path],
    bval: list[Path],
    bvec: list[Path],
    pe_dir: list[str],
    pe_data: list[np.ndarray],
    phenc: Path | None,
    indices: list[str] | None,
    topup: fsl.TopupOutputs | None,
    eddy_opts: EddyConfig | None = EddyConfig(),
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    working_dir: Path = Path.cwd() / "tmp",
    output_dir: Path = Path.cwd(),
    **kwargs,
) -> tuple[Path, Path, Path]:
    """Perform FSL's eddy.

    Args:
        dwi: List of diffusion file paths to process.
        bval: List of diffusion associated bval file paths.
        bvec: List of diffusion associated bvec file paths.
        pe_dir: List of phase encoding directions for each 4D volume.
        pe_data: List of phase encoding data for each 4D volume.
        phenc: Path to phase encoding data file.
        indices: List of indices associated with each volume.
        topup: If performed, topup outputs to be used.
        eddy_opts: Eddy configuration options.
        bids: Function to generate BIDS file paths.
        working_dir: Working directory to store intermediate outputs.
        output_dir: Output directory to save files.
        **kwargs: Arbitrary keyword input arguments.

    Returns:
        A 3-tuple, with the eddy corrected nifti file path, the associated bval and
        rotated bvec file paths.

    Raises:
        ValueError: If multiple diffusion-associated files found and step to be skipped.
    """
    if not isinstance(eddy_opts, EddyConfig):
        raise TypeError(f"Expected EddyConfig, got {type(eddy_opts)}")
    logger = kwargs.get("logger", logging.Logger(__name__))

    if eddy_opts.skip:
        if any((len(dwi) > 1, len(bvec) > 1, len(bval) > 1)):
            raise ValueError("Multiple diffusion-associated files found")
        logger.info("Skipping FSL's Eddy")
        return dwi[0], bval[0], bvec[0]

    logger.info("Performing FSL's Eddy")
    dwi_cat, bval_cat, bvec_cat, phenc, index_fpath = gen_eddy_inputs(
        dwi=dwi,
        bval=bval,
        bvec=bvec,
        pe_dir=pe_dir,
        pe_data=pe_data,
        phenc=phenc,
        indices=indices,
        bids=bids,
        output_dir=working_dir,
    )
    # Generate crude mask for eddy
    mask = mrtrix.dwi2mask(
        input_=dwi_cat,
        output=bids(desc="preEddy", suffix="mask", ext=".nii.gz"),
        fslgrad=mrtrix.dwi2mask_fslgrad(bvecs=bvec_cat, bvals=bval_cat),
    ).output
    bids = partial(bids, desc="eddy")
    eddy = fsl.eddy(
        imain=dwi_cat,
        mask=mask,
        bvecs=bvec_cat,
        bvals=bval_cat,
        acqp=phenc,
        index=index_fpath,
        topup="_".join(str(topup.movpar).split("_")[:-1]) if topup else None,
        out=bids(),
        slm=eddy_opts.slm,
        cnr_maps=eddy_opts.cnr,
        repol=eddy_opts.repol,
        residuals=eddy_opts.residuals,
        data_is_shelled=eddy_opts.shelled,
    )

    if eddy_opts.cnr:
        cnr_fpath = Path(eddy.cnr_maps).with_name(bids(suffix="cnrmap", ext=".nii.gz"))
        niwrap_helper.save(files=cnr_fpath, out_dir=output_dir)
    if eddy_opts.residuals:
        residuals_fpath = Path(eddy.residuals).with_name(
            bids(suffix="residuals", ext=".nii.gz")
        )
        niwrap_helper.save(files=residuals_fpath, out_dir=output_dir)

    return eddy.out, bval_cat, eddy.rotated_bvecs
