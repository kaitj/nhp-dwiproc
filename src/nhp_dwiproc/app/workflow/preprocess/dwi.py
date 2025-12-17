"""Sub-module associated with processing dwi images (e.g. split, concat, etc)."""

import logging
from functools import partial
from pathlib import Path
from typing import Any

import niwrap_helper
import numpy as np
from niwrap import mrtrix
from niwrap_helper.types import StrPath

from nhp_dwiproc.app.lib.dwi import (
    concat_dir_phenc_data,
    get_eddy_indices,
    get_pe_indices,
    get_phenc_info,
    normalize,
)
from nhp_dwiproc.config.preprocess import MetadataConfig


def get_phenc_data(
    dwi: Path,
    bval: Path,
    bvec: Path,
    json: dict[str, Any],
    idx: int,
    metadata_opts: MetadataConfig = MetadataConfig(),
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
    **kwargs,
) -> tuple[Path, str, np.ndarray]:
    """Generate phase-encoding direction data.

    Args:
        dwi: File path to diffusion nifti.
        bval: File path to diffusion bval.
        bvec: File path to diffusion bvec.
        json: Metadata associated with diffusion.
        idx: Index of diffusion volume.
        metadata_opts: Metadata configuration options.
        bids: Function to generate bids file path.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        A 3-tuple - a B0, phase encoding direction, and phase encoding data.
    """
    if not isinstance(metadata_opts, MetadataConfig):
        raise TypeError(f"Expected DenoiseConfig, got {type(metadata_opts)}")
    logger = kwargs.get("logger", logging.Logger(__name__))

    logger.info("Getting phase-encoding information")
    bids = partial(bids, suffix="b0")
    dwi_b0 = mrtrix.dwiextract(
        input_=dwi,
        output=bids(ext=".mif"),
        bzero=True,
        fslgrad=mrtrix.dwiextract_fslgrad(bvals=bval, bvecs=bvec),
    )
    dwi_b0 = mrtrix.mrconvert(
        input_=dwi_b0.output,
        output=bids(ext=".nii.gz"),
        coord=[mrtrix.mrconvert_coord(axis=3, selection=[0])],
        axes=[0, 1, 2],
    )
    pe_dir, pe_data = get_phenc_info(
        nii=dwi,
        json=json,
        idx=idx,
        pe_dirs=metadata_opts.pe_dirs,
        echo_spacing=None
        if metadata_opts.echo_spacing is None
        else str(metadata_opts.echo_spacing),
        logger=logger,
    )
    return dwi_b0.output, pe_dir, pe_data


def gen_topup_inputs(
    b0: list[Path],
    pe_data: list[np.ndarray],
    pe_dir: list[str],
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: StrPath = Path.cwd(),
) -> tuple[Path, Path, list[str]]:
    """Generate concatenated inputs for topup.

    Args:
        b0: List of b0 nifti file paths to process.
        pe_data: List of phase-encoding data associated with each b0.
        pe_dir: List of phase encoding directions.
        bids: Function to generate bids file name.
        output_dir: Working directry to output files to.

    Returns:
        A 3-tuple, with the phase encoding file path, normalized output file path, and
        phase-encoding indices.
    """
    dwi_b0 = mrtrix.mrcat(
        image1=b0[0],
        image2=b0[1:],  # type: ignore
        output=bids(suffix="b0", ext=".nii.gz"),
    )
    output_dir = Path(output_dir) / f"{niwrap_helper.gen_hash()}_normalize"
    dwi_fpath = normalize(dwi_b0.output, bids=bids, output_dir=output_dir)

    # Get matching PE data to b0
    output_dir = output_dir.parent / f"{niwrap_helper.gen_hash()}_concat-phenc"
    phenc_fpath = concat_dir_phenc_data(
        pe_data=pe_data, bids=bids, output_dir=output_dir
    )
    pe_indices = get_pe_indices(pe_dir)
    return phenc_fpath, dwi_fpath, pe_indices


def concat_bv(
    bvals: list[Path],
    bvecs: list[Path],
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: StrPath = Path.cwd(),
) -> tuple[Path, Path]:
    """Concatenate .bval and .bvec files.

    Args:
        bvals: List of diffusion bval file paths to concatenate.
        bvecs: List of diffusion bvec file paths to concatenate.
        bids: Function to generate BIDS file name.
        output_dir: Working directory to output files to.

    Returns:
        A 2-tuple, with concatenated bval and bvec file paths.
    """
    output_dir = Path(output_dir) / f"{niwrap_helper.gen_hash()}_concat-bv"
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
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: StrPath = Path.cwd() / "tmp",
) -> tuple[Path, ...]:
    """Generate concatenated inputs for eddy.

    Args:
        dwi: List of diffusion file paths to process.
        bval: List of diffusion associated bval file paths.
        bvec: List of diffusion associated bvec file paths.
        pe_dir: List of phase encoding directions for each 4D volume.
        pe_data: List of phase encoding data for each 4D volume.
        phenc: Path to phase encoding data file.
        indices: List of indices associated with each volume.
        bids: Function to generate BIDS file paths.
        output_dir: Working directory to store intermediate outputs.

    Return:
        A 5-tuple with concatenated diffusion, bval, bvec, phase encoding data file
        and index file paths.
    """
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
            pe_data=[pe_data[0]],
            bids=bids,
            output_dir=Path(output_dir) / f"{niwrap_helper.gen_hash()}_concat-phenc",
        )
    # Generate index file
    index_fpath = get_eddy_indices(
        niis=dwi, indices=indices, bids=bids, output_dir=output_dir
    )
    return dwi_concat, bval_concat, bvec_concat, phenc, index_fpath
