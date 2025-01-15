"""Helper functions for generating diffusion related files for workflow."""

import pathlib as pl
from logging import Logger
from typing import Any

import nibabel.nifti1 as nib
import numpy as np
from niwrap import mrtrix

from nhp_dwiproc.app import utils
from nhp_dwiproc.lib import metadata
from nhp_dwiproc.lib.utils import gen_hash, load_nifti


def get_phenc_info(
    idx: int,
    input_data: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[str, np.ndarray]:
    """Generate phase encode information file."""
    # Gather relevant metadata
    eff_echo = metadata.echo_spacing(
        dwi_json=input_data["dwi"]["json"], logger=logger, **kwargs
    )
    pe_dir = metadata.phase_encode_dir(
        idx=idx, dwi_json=input_data["dwi"]["json"], logger=logger, **kwargs
    )
    # Determine corresponding phase-encoding vector, set accordingly
    possible_vecs = {
        "i": np.array([1, 0, 0]),
        "j": np.array([0, 1, 0]),
        "k": np.array([0, 0, 1]),
    }
    pe_vec = possible_vecs[pe_dir[0]]
    if len(pe_dir) == 2 and pe_dir.endswith("-"):
        pe_vec[np.where(pe_vec > 0)] = -1

    # Generate phase encoding data for use
    img = nib.load(input_data["dwi"]["nii"])
    img_size = np.array(img.header.get_data_shape())
    num_phase_encodes = img_size[np.where(np.abs(pe_vec) > 0)]
    ro_time = eff_echo * (num_phase_encodes - 1)
    if ro_time > 0.2:
        logger.warning(
            "Read-out time greater than eddy expected 0.2 - using half of echo spacing"
        )
        ro_time /= 2
    elif ro_time < 0.01:
        logger.warning(
            "Read-out time less than eddy expected 0.01 - using double of echo spacing"
        )
        ro_time *= 2
    pe_line = np.hstack([pe_vec, np.array(ro_time)])
    pe_data = np.array([pe_line])

    return pe_dir, pe_data


def concat_dir_phenc_data(
    pe_data: list[np.ndarray],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    **kwargs,
) -> pl.Path:
    """Concatenate opposite phase encoding directions."""
    phenc_fname = utils.bids_name(
        datatype="dwi", desc="concat", suffix="phenc", ext=".txt", **input_group
    )
    phenc_fpath = cfg["opt.working_dir"] / f"{gen_hash()}_concat-phenc" / phenc_fname
    phenc_fpath.parent.mkdir(parents=True, exist_ok=False)
    np.savetxt(phenc_fpath, np.vstack(pe_data), fmt="%.5f")

    return phenc_fpath


def normalize(
    img: str | pl.Path, input_group: dict[str, Any], cfg: dict[str, Any], **kwargs
) -> pl.Path:
    """Normalize 4D image."""
    nii = load_nifti(img)
    arr = np.array(nii.dataobj)

    ref_mean = np.mean(arr[..., 0])

    for idx in range(arr.shape[-1]):
        slice_mean = np.mean(arr[..., idx])
        if not np.isclose(slice_mean, 0.0):
            arr[..., idx] *= ref_mean / slice_mean

    norm_nii = nib.Nifti1Image(dataobj=arr, affine=nii.affine, header=nii.header)

    nii_fname = utils.bids_name(
        datatype="dwi", desc="normalized", suffix="b0", ext=".nii.gz", **input_group
    )
    nii_fpath = cfg["opt.working_dir"] / f"{gen_hash()}_normalize" / nii_fname
    nii_fpath.parent.mkdir(parents=True, exist_ok=False)
    nib.save(norm_nii, nii_fpath)

    return nii_fpath


def get_pe_indices(pe_dirs: list[str]) -> list[str]:
    """Get PE indices - LR/RL if available, AP otherwise."""
    indices: dict[str, list[Any]] = {"lr": [], "ap": []}
    pe: dict[str, list[Any]] = {
        "axe": [ax[0] for ax in pe_dirs],
        "dir": [ax[1:] for ax in pe_dirs],
    }

    # If multiple directions, use LR indices if possible, else use AP
    if len(set(pe_dirs)) > 1:
        for idx, ax in enumerate(pe["axe"]):
            idxes = idx + 1
            if ax == "i":
                indices["lr"].append(str(idxes))
            elif ax == "j":
                indices["ap"].append(str(idxes))
        return indices["lr"] if len(set(indices["lr"])) == 2 else indices["ap"]
    else:
        return ["1"] * len(pe["axe"])


def get_eddy_indices(
    niis: list[str | pl.Path],
    indices: list[str] | None,
    input_group: dict[str, Any],
    cfg: dict[str, Any],
) -> pl.Path:
    """Generate dwi index file for eddy."""
    imsizes = [nib.load(nii).header.get_data_shape() for nii in niis]

    eddy_idxes = [
        idx if len(imsize) < 4 else [idx] * imsize[3]
        for idx, imsize in zip(indices or ["1"] * len(imsizes), imsizes)
    ]

    out_dir = cfg["opt.working_dir"] / f"{gen_hash()}_eddy-indices"
    out_fname = utils.bids_name(
        datatype="dwi", desc="eddy", suffix="indices", ext=".txt", **input_group
    )
    out_fpath = out_dir / out_fname
    out_fpath.parent.mkdir(parents=True, exist_ok=False)
    np.savetxt(out_fpath, np.array(eddy_idxes).flatten(), fmt="%s", newline=" ")

    return out_fpath


def rotate_bvec(
    bvec_file: pl.Path,
    transformation: pl.Path,
    cfg: dict[str, Any],
    input_group: dict[str, Any],
    **kwargs,
) -> pl.Path:
    """Rotate bvec file."""
    bvec = np.loadtxt(bvec_file)
    transformation_mat = np.loadtxt(transformation)
    rotated_bvec = np.dot(transformation_mat[:3, :3], bvec)

    out_dir = cfg["opt.working_dir"] / f"{gen_hash()}_rotate-bvec"
    out_fname = utils.bids_name(
        datatype="dwi",
        space="T1w",
        res="dwi",
        desc="preproc",
        suffix="dwi",
        ext=".bvec",
        **input_group,
    )
    out_fpath = out_dir / out_fname
    out_fpath.parent.mkdir(parents=True, exist_ok=False)
    np.savetxt(out_fpath, rotated_bvec, fmt="%.5f")

    return out_fpath


def grad_check(
    nii: pl.Path,
    bvec: pl.Path,
    bval: pl.Path,
    mask: pl.Path | None,
    cfg: dict[str, Any],
    **kwargs,
) -> None:
    """Check and update orientation of diffusion gradient."""
    bvec_check = mrtrix.dwigradcheck(
        input_image=nii,
        mask_image=mask,
        number=10_000,  # Small number to enable quick permutations,
        fslgrad=mrtrix.DwigradcheckFslgrad(
            bvecs=bvec,
            bvals=bval,
        ),
        export_grad_fsl=mrtrix.DwigradcheckExportGradFsl(
            bvecs_path=bval.with_suffix(".bvec").name,
            bvals_path=bval.name,  # replacing file if necessary
        ),
        nthreads=cfg["opt.threads"],
    )
    if not bvec_check.export_grad_fsl_:
        raise AttributeError("Unsuccessful export of diffusion gradients")

    utils.io.save(
        files=bvec_check.export_grad_fsl_.bvecs_path,
        out_dir=bval.parent,
    )
