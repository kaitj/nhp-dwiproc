"""Helper functions for generating diffusion related files for workflow."""

from functools import partial
from logging import Logger
from pathlib import Path
from typing import Any

import nibabel.nifti1 as nib
import niwrap_helper
import numpy as np
from niwrap import mrtrix
from niwrap_helper.types import StrPath

from ..lib import metadata


def get_phenc_info(
    nii: Path,
    json: dict[str, Any],
    idx: int,
    pe_dirs: list[str] | None = None,
    echo_spacing: str | None = None,
    logger: Logger = Logger(name=__name__),
) -> tuple[str, np.ndarray]:
    """Generate phase encode information file.

    Args:
        nii: Input nifti file path.
        json: Associated nifti metadata.
        idx: Nifti volume index.
        pe_dirs: Phase encoding directions, if provided.
        echo_spacing: Echo spacing for all directions if provided.
        logger: Logger object.

    Returns:
        A 2-tuple, with phase encoding direction, and phase encoding data.
    """
    # Gather relevant metadata
    eff_echo = metadata.echo_spacing(
        dwi_json=json, echo_spacing=echo_spacing, logger=logger
    )
    pe_dir = metadata.phase_encode_dir(
        idx=idx, dwi_json=json, pe_dirs=pe_dirs, logger=logger
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
    img = nib.load(nii)
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
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: StrPath = Path.cwd(),
) -> Path:
    """Concatenate opposite phase encoding directions."""
    phenc_fpath = Path(output_dir) / bids(desc="concat", suffix="phenc", ext=".txt")
    phenc_fpath.parent.mkdir(parents=True, exist_ok=False)
    np.savetxt(phenc_fpath, np.vstack(pe_data), fmt="%.5f")

    return phenc_fpath


def normalize(
    img: str | Path,
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: StrPath = Path.cwd(),
) -> Path:
    """Normalize 4D image."""
    nii = nib.load(img)
    arr = np.array(nii.dataobj)
    ref_mean = np.mean(arr[..., 0])

    for idx in range(arr.shape[-1]):
        slice_mean = np.mean(arr[..., idx])
        if not np.isclose(slice_mean, 0.0):
            arr[..., idx] *= ref_mean / slice_mean

    norm_nii = nib.Nifti1Image(dataobj=arr, affine=nii.affine, header=nii.header)
    nii_fname = bids(desc="normalized", suffix="b0", ext=".nii.gz")
    nii_fpath = Path(output_dir) / nii_fname
    nii_fpath.parent.mkdir(parents=True, exist_ok=False)
    nib.save(norm_nii, nii_fpath)

    return nii_fpath


def get_pe_indices(pe_dir: list[str]) -> list[str]:
    """Get PE indices - LR/RL if available, AP otherwise."""
    indices: dict[str, list[Any]] = {"lr": [], "ap": []}
    pe: dict[str, list[Any]] = {
        "axe": [ax[0] for ax in pe_dir],
        "dir": [ax[1:] for ax in pe_dir],
    }

    # If multiple directions, use LR indices if possible, else use AP
    if len(set(pe_dir)) > 1:
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
    niis: list[Path],
    indices: list[str] | None,
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: StrPath = Path.cwd() / "tmp",
) -> Path:
    """Generate dwi index file for eddy."""
    imsizes = [nib.load(nii).header.get_data_shape() for nii in niis]

    eddy_idxes = [
        idx if len(imsize) < 4 else [idx] * imsize[3]
        for idx, imsize in zip(indices or ["1"] * len(imsizes), imsizes)
    ]

    output_dir = Path(output_dir) / f"{niwrap_helper.gen_hash()}_eddy-indices"
    out_fpath = output_dir / bids(desc="eddy", suffix="indices", ext=".txt")
    out_fpath.parent.mkdir(parents=True, exist_ok=False)
    np.savetxt(out_fpath, np.array(eddy_idxes).flatten(), fmt="%s", newline=" ")
    return out_fpath


def rotate_bvec(
    bvec_file: Path,
    transformation: Path,
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: StrPath = Path.cwd() / "tmp",
) -> Path:
    """Rotate bvec file."""
    bvec = np.loadtxt(bvec_file)
    transformation_mat = np.loadtxt(transformation)
    rotated_bvec = np.dot(transformation_mat[:3, :3], bvec)

    out_dir = Path(output_dir) / f"{niwrap_helper.gen_hash()}_rotate-bvec"
    out_fname = bids(space="T1w", res="dwi", desc="preproc", suffix="dwi", ext=".bvec")
    out_fpath = out_dir / out_fname
    out_fpath.parent.mkdir(parents=True, exist_ok=False)
    np.savetxt(out_fpath, rotated_bvec, fmt="%.5f")
    return out_fpath


def grad_check(nii: Path, bvec: Path, bval: Path, mask: Path | None, **kwargs) -> None:
    """Check and update orientation of diffusion gradient.

    Args:
        nii: Path to dwi nifti.
        bvec: Path to dwi bvec.
        bval: Path to dwi bval.
        mask: Path to mask nifti.
        **kwargs: Arbitrary keyword arguments

    Raises:
        AttributeError: If unable to successfully export diffusion gradients.
    """
    bvec_check = mrtrix.dwigradcheck(
        input_image=nii,
        mask_image=mask,
        number=10_000,  # Small number to enable quick permutations,
        fslgrad=mrtrix.dwigradcheck_fslgrad_params(bvecs=bvec, bvals=bval),
        export_grad_fsl=mrtrix.dwigradcheck_export_grad_fsl_params(
            bvecs_path=bval.with_suffix(".bvec").name,
            bvals_path=bval.name,
        ),
    )
    if not bvec_check.export_grad_fsl_:
        raise AttributeError("Unsuccessful export of diffusion gradients")
    niwrap_helper.save(
        files=bvec_check.export_grad_fsl_.bvecs_path, out_dir=bval.parent
    )
