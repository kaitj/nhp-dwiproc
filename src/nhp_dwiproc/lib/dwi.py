"""Helper functions for generating diffusion related files for workflow."""

import json
import pathlib as pl
from logging import Logger
from typing import Any

import nibabel as nib
import numpy as np

from nhp_dwiproc.app import utils
from nhp_dwiproc.lib import metadata
from nhp_dwiproc.lib.utils import gen_hash


def get_phenc_info(
    idx: int,
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[str, np.ndarray]:
    """Generate phase encode information file."""
    with open(input_data["dwi"]["json"], "r") as fpath:
        dwi_json = json.load(fpath)

    # Gather relevant metadata
    eff_echo = metadata.echo_spacing(dwi_json=dwi_json, cfg=cfg, logger=logger)
    pe_dir = metadata.phase_encode_dir(
        idx=idx, dwi_json=dwi_json, cfg=cfg, logger=logger
    )
    # Determine corresponding phase-encoding vector, set accordingly
    possible_vecs = {
        "i": np.array([1, 0, 0]),
        "j": np.array([0, 1, 0]),
        "k": np.array([0, 0, 1]),
    }
    pe_vec = possible_vecs[pe_dir]
    if len(pe_dir) == 2 and pe_dir.endswith("-"):
        pe_vec[np.where(pe_vec > 0)] = -1

    # Generate phase encoding data for use
    img = nib.loadsave.load(input_data["dwi"]["nii"])
    img_size = np.array(img.header.get_data_shape())
    num_phase_encodes = img_size[np.where(np.abs(pe_vec) > 0)]
    pe_line = np.hstack([pe_vec, np.array(eff_echo * num_phase_encodes)])
    pe_data = (
        np.tile(pe_line, [img_size[3], 1])
        if len(img_size) == 4
        else np.array([pe_line])
    )

    return pe_dir, pe_data


def concat_dir_phenc_data(
    pe_data: list[np.ndarray],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    **kwargs,
) -> pl.Path:
    """Concatenate opposite phase encoding directions."""
    hash = gen_hash()
    phenc_fname = utils.bids_name(
        datatype="dwi", desc="concat", suffix="phenc", ext=".txt", **input_group
    )
    phenc_fpath = cfg["opt.working_dir"] / hash / phenc_fname
    np.savetxt(phenc_fpath, np.vstack(pe_data), fmt="%.5f")

    return phenc_fpath


def normalize(
    img: str | pl.Path, input_group: dict[str, Any], cfg: dict[str, Any], **kwargs
) -> pl.Path:
    """Normalize 4D image."""
    nii = nib.loadsave.load(img)
    arr = nii.dataobj

    ref_mean = np.mean(arr[..., 0])

    for idx in range(arr.shape[-1]):
        slice_mean = np.mean(arr[..., idx])
        if not np.isclose(slice_mean, 0.0):
            arr[..., idx] *= ref_mean / slice_mean

    norm_nii = nib.nifti1.Nifti1Image(dataobj=arr, affine=nii.affine, header=nii.header)

    hash = gen_hash()
    nii_fname = utils.bids_name(
        datatype="dwi", desc="normalized", suffix="b0", ext=".nii.gz", **input_group
    )
    nii_fpath = cfg["opt.working_dir"] / hash / nii_fname
    nib.loadsave.save(norm_nii, nii_fpath)

    return nii_fpath


def get_pe_indices(pe_dirs: list[str]) -> list[str]:
    """Get PE indices - LR/RL if available, AP otherwise."""
    indices: dict[str, list[Any]] = {"lr": [], "ap": []}
    pe: dict[str, list[Any]] = {
        "axe": [ax[0] for ax in pe_dirs],
        "dir": [ax[1:] for ax in pe_dirs],
    }

    if len(set(pe["axe"])) > 1:
        for idx, pe in enumerate(pe["axe"]):
            if pe == "i":
                indices["lr"].append(idx)
            elif pe == "j":
                indices["ap"].append(idx)
        return (
            indices["lr"]
            if len(set([pe_dirs[idx] for idx in indices["lr"]])) == 2
            else indices["ap"]
        )
    else:
        return [str(idx) for idx in range(len(pe["axe"]))]


def get_eddy_indices(
    niis: list[str | pl.Path], input_group: dict[str, Any], cfg: dict[str, Any]
) -> pl.Path:
    """Generate dwi index file for eddy."""
    imsizes = [nib.loadsave.load(nii).header.get_data_shape() for nii in niis]

    eddy_idxes = []
    for idx, im in enumerate(imsizes, start=1):
        if len(im) < 4:
            eddy_idxes.append(idx)
        else:
            eddy_idxes.extend([idx] * im[3])

    out_dir = cfg["opt.working_dir"] / gen_hash()
    out_fname = utils.bids_name(
        datatype="dwi", desc="eddy", suffix="indices", ext=".txt", **input_group
    )
    out_fpath = out_dir / out_fname
    np.savetxt(out_fpath, np.array(eddy_idxes), fmt="%d")

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

    out_dir = cfg["opt.working_dir"] / gen_hash()
    out_fname = utils.bids_name(
        datatype="dwi", space="T1w", res="dwi", suffix="dwi", ext=".bvec", **input_group
    )
    out_fpath = out_dir / out_fname
    np.savetxt(out_fpath, rotated_bvec, fmt="%.5f")

    return out_fpath
