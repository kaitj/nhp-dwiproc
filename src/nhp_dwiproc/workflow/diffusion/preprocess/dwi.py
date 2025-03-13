"""Sub-module associated with processing dwi images (e.g. split, concat, etc)."""

from functools import partial
from logging import Logger
from pathlib import Path
from typing import Any

import numpy as np
from niwrap import mrtrix

import nhp_dwiproc.utils as utils
from nhp_dwiproc.lib.dwi import (
    concat_dir_phenc_data,
    get_eddy_indices,
    get_pe_indices,
    get_phenc_info,
    normalize,
)


def get_phenc_data(
    dwi: Path,
    bval: Path,
    bvec: Path,
    json: dict[str, Any],
    idx: int,
    pe_dirs: list[str] | None = None,
    echo_spacing: str | None = None,
    logger: Logger = Logger(name="logger"),
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
) -> tuple[Path, str, np.ndarray]:
    """Generate phase-encoding direction data for downstream steps."""
    logger.info("Getting phase-encoding information")
    bids = partial(bids, suffix="b0")
    dwi_b0 = mrtrix.dwiextract(
        input_=dwi,
        output=bids(ext=".mif"),
        bzero=True,
        fslgrad=mrtrix.dwiextract_fslgrad_params(bvals=bval, bvecs=bvec),
    )

    dwi_b0 = mrtrix.mrconvert(
        input_=dwi_b0.output,
        output=bids(ext=".nii.gz"),
        coord=[mrtrix.mrconvert_coord_params(3, [0])],
        axes=[0, 1, 2],
    )

    pe_dir, pe_data = get_phenc_info(
        nii=dwi,
        json=json,
        idx=idx,
        pe_dirs=pe_dirs,
        echo_spacing=echo_spacing,
        logger=logger,
    )
    return dwi_b0.output, pe_dir, pe_data


def gen_topup_inputs(
    b0: list[Path],
    pe_data: list[np.ndarray],
    pe_dir: list[str],
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
    output_dir: Path = Path.cwd(),
) -> tuple[Path, Path, list[str]]:
    """Generate concatenated inputs for topup."""
    dwi_b0 = mrtrix.mrcat(
        image1=b0[0],
        image2=b0[1:],  # type: ignore
        output=bids(suffix="b0", ext=".nii.gz"),
    )
    output_dir = output_dir / f"{utils.assets.gen_hash()}_normalize"
    dwi_fpath = normalize(dwi_b0.output, bids=bids, output_dir=output_dir)

    # Get matching PE data to b0
    output_dir = output_dir.parent / f"{utils.assets.gen_hash()}_concat-phenc"
    phenc_fpath = concat_dir_phenc_data(
        pe_data=pe_data, bids=bids, output_dir=output_dir
    )
    pe_indices = get_pe_indices(pe_dir)

    return phenc_fpath, dwi_fpath, pe_indices


def concat_bv(
    bvals: list[Path],
    bvecs: list[Path],
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
    output_dir: Path = Path.cwd(),
) -> tuple[Path, Path]:
    """Concatenate .bval and .bvec files."""
    output_dir = output_dir / f"{utils.assets.gen_hash()}_concat-bv"
    output_dir.mkdir(parents=True, exist_ok=False)
    bids = partial(bids, desc="concat", suffix="dwi")
    out_files = output_dir / bids(ext=".bval"), output_dir / bids(ext=".bvec")

    for in_bvs, out_bv in zip([bvals, bvecs], list(out_files)):
        concat_bv = np.hstack([np.loadtxt(bv, ndmin=2) for bv in in_bvs])
        np.savetxt(out_bv, concat_bv, fmt="%.5f")

    return out_files


def gen_eddy_inputs(
    dwi: list[Path],
    bval: list[Path],
    bvec: list[Path],
    pe_dir: list[str],
    pe_data: list[np.ndarray],
    phenc: Path | None,
    indices: list[str] | None,
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
    output_dir: Path = Path.cwd() / "tmp",
) -> tuple[Path, ...]:
    """Generate concatenated inputs for eddy."""
    # Concatenate image
    if len(set(pe_dir)) > 1:
        dwi_concat = mrtrix.mrcat(
            image1=dwi[0],
            image2=dwi[1:],  # type: ignore
            output=bids(desc="concat", suffix="dwi", ext=".nii.gz"),
        ).output
    else:
        dwi_concat = dwi[0]

    # Concatenate bval / bvec
    bval_concat, bvec_concat = concat_bv(
        bvals=bval, bvecs=bvec, bids=bids, output_dir=output_dir
    )

    # Generate phenc file if necessary
    if not phenc:
        phenc = concat_dir_phenc_data(
            pe_data=[pe_data[0]], bids=bids, output_dir=output_dir
        )

    # Generate index file
    index_fpath = get_eddy_indices(
        niis=dwi, indices=indices, bids=bids, output_dir=output_dir
    )

    return dwi_concat, bval_concat, bvec_concat, phenc, index_fpath
