"""Preprocess steps associated with FSL's eddy."""

from functools import partial
from pathlib import Path

import niwrap_helper
import numpy as np
from niwrap import fsl, mrtrix

import nhp_dwiproc.utils as utils
from nhp_dwiproc.workflow.diffusion.preprocess.dwi import gen_eddy_inputs


def run_eddy(
    dwi: list[Path],
    bval: list[Path],
    bvec: list[Path],
    pe_dir: list[str],
    pe_data: list[np.ndarray],
    phenc: Path | None,
    indices: list[str] | None,
    topup: fsl.TopupOutputs | None,
    slm: str | None,
    cnr_maps: bool,
    repol: bool,
    residuals: bool,
    shelled: bool,
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    working_dir: Path = Path.cwd() / "tmp",
    output_dir: Path = Path.cwd(),
    **kwargs,
) -> tuple[Path, Path, Path]:
    """Perform FSL's eddy."""
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
        fslgrad=mrtrix.dwi2mask_fslgrad_params(bvecs=bvec_cat, bvals=bval_cat),
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
        slm=slm,  # type: ignore
        cnr_maps=cnr_maps,
        repol=repol,
        residuals=residuals,
        data_is_shelled=shelled,
    )

    if cnr_maps:
        cnr_fpath = utils.io.rename(
            old_fpath=eddy.cnr_maps, new_fname=bids(suffix="cnrmap", ext=".nii.gz")
        )
        utils.io.save(files=cnr_fpath, out_dir=output_dir)
    if residuals:
        residuals_fpath = utils.io.rename(
            old_fpath=eddy.residuals, new_fname=bids(suffix="residuals", ext=".nii.gz")
        )
        utils.io.save(files=residuals_fpath, out_dir=output_dir)

    return eddy.out, bval_cat, eddy.rotated_bvecs
