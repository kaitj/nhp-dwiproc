"""Sub-module associated with processing dwi images (e.g. split, concat, etc)."""

import pathlib as pl
from functools import partial
from logging import Logger
from typing import Any

import numpy as np
from niwrap import mrtrix
from styxdefs import InputPathType, OutputPathType

import nhp_dwiproc.utils as utils
from nhp_dwiproc.lib.dwi import (
    concat_dir_phenc_data,
    get_eddy_indices,
    get_pe_indices,
    get_phenc_info,
    normalize,
)


def get_phenc_data(
    dwi: InputPathType,
    idx: int,
    entities: dict[str, Any],
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> tuple[OutputPathType, str, np.ndarray]:
    """Generate phase-encoding direction data for downstream steps."""
    logger.info("Getting phase-encoding information")
    bids = partial(utils.io.bids_name, datatype="dwi", suffix="b0", **entities)
    dwi_b0 = mrtrix.dwiextract(
        input_=dwi,
        output=bids(ext=".mif"),
        bzero=True,
        fslgrad=mrtrix.DwiextractFslgrad(
            bvals=input_data["dwi"]["bval"],
            bvecs=input_data["dwi"]["bvec"],
        ),
        nthreads=cfg["opt.threads"],
    )

    dwi_b0 = mrtrix.mrconvert(
        input_=dwi_b0.output,
        output=bids(ext=".nii.gz"),
        coord=[mrtrix.MrconvertCoord(3, [0])],
        axes=[0, 1, 2],
        nthreads=cfg["opt.threads"],
    )

    pe_dir, pe_data = get_phenc_info(
        idx=idx,
        input_data=input_data,
        cfg=cfg,
        logger=logger,
    )
    return (
        dwi_b0.output,
        pe_dir,
        pe_data,
    )


def gen_topup_inputs(
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    **kwargs,
) -> tuple[pl.Path, pl.Path, list[str]]:
    """Generate concatenated inputs for topup."""
    dwi_b0 = mrtrix.mrcat(
        image1=dir_outs["b0"][0],
        image2=dir_outs["b0"][1:],
        output=utils.io.bids_name(
            datatype="dwi", suffix="b0", ext=".nii.gz", **input_group
        ),
        nthreads=cfg["opt.threads"],
    )
    dwi_b0 = dwi_b0.output
    dwi_fpath = normalize(dwi_b0, input_group=input_group, cfg=cfg)

    # Get matching PE data to b0
    phenc_fpath = concat_dir_phenc_data(
        pe_data=dir_outs["pe_data"],
        input_group=input_group,
        cfg=cfg,
    )
    pe_indices = get_pe_indices(dir_outs["pe_dir"])

    return phenc_fpath, dwi_fpath, pe_indices


def concat_bv(
    bvals: list[str | pl.Path],
    bvecs: list[str | pl.Path],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    **kwargs,
) -> tuple[pl.Path, ...]:
    """Concatenate .bval and .bvec files."""
    out_dir = cfg["opt.working_dir"] / f"{utils.assets.gen_hash()}_concat-bv"
    bids = partial(
        utils.io.bids_name, datatype="dwi", desc="concat", suffix="dwi", **input_group
    )
    out_dir.mkdir(parents=True, exist_ok=False)
    out_files = out_dir / bids(ext=".bval"), out_dir / bids(ext=".bvec")

    for in_bvs, out_bv in zip([bvals, bvecs], list(out_files)):
        concat_bv = np.hstack([np.loadtxt(bv, ndmin=2) for bv in in_bvs])
        np.savetxt(out_bv, concat_bv, fmt="%.5f")

    return out_files


def gen_eddy_inputs(
    phenc: pl.Path | None,
    indices: list[str] | None,
    dir_outs: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    **kwargs,
) -> tuple[pl.Path, ...]:
    """Generate concatenated inputs for eddy."""
    # Concatenate image
    if len(set(dir_outs["pe_dir"])) > 1:
        dwi = mrtrix.mrcat(
            image1=dir_outs["dwi"][0],
            image2=dir_outs["dwi"][1:],
            output=utils.io.bids_name(
                datatype="dwi",
                desc="concat",
                suffix="dwi",
                ext=".nii.gz",
                **input_group,
            ),
            nthreads=cfg["opt.threads"],
        )
        dwi = dwi.output
    else:
        dwi = dir_outs["dwi"][0]

    # Concatenate bval / bvec
    bval, bvec = concat_bv(
        bvals=dir_outs["bval"],
        bvecs=dir_outs["bvec"],
        input_group=input_group,
        cfg=cfg,
        **kwargs,
    )

    # Generate phenc file if necessary
    if not phenc:
        phenc = concat_dir_phenc_data(
            pe_data=[dir_outs["pe_data"][0]],
            input_group=input_group,
            cfg=cfg,
        )

    # Generate index file
    index_fpath = get_eddy_indices(
        niis=dir_outs["dwi"], indices=indices, input_group=input_group, cfg=cfg
    )

    return dwi, bval, bvec, phenc, index_fpath
