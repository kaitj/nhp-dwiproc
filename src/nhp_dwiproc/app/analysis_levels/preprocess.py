"""Preprocessing of participants."""

import json
import logging
import shutil
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import Any, DefaultDict

import polars as pl
from bids2table import parse_bids_entities
from niwrap import GraphRunner, LocalRunner, Runner
from niwrap_helper import bids_path, cleanup
from niwrap_helper.types import StrPath
from tqdm import tqdm

from nhp_dwiproc import config as cfg_
from nhp_dwiproc.app import io, utils
from nhp_dwiproc.app.lib import dwi as dwi_lib
from nhp_dwiproc.app.workflow import preprocess


def run(
    input_dir: StrPath,
    output_dir: StrPath,
    preproc_opts: cfg_.PreprocessConfig = cfg_.PreprocessConfig(),
    global_opts: cfg_.GlobalOptsConfig = cfg_.GlobalOptsConfig(),
    runner: Runner = LocalRunner(),
    logger: logging.Logger = logging.Logger(__name__),
) -> None:
    """Runner for preprocess analysis-level.

    Args:
        input_dir: Input dataset directory path.
        output_dir: Output directory.
        preproc_opts: Preprocessing stage config options.
        global_opts: Global config options.
        runner: StyxRunner used.
        logger: Logger object.

    Returns:
        None

    Raises:
        TypeError: If configs of an unexpected type.
        ValueError: If data is missing.
    """
    stage = "preprocess"
    logger.info(f"Performing '{stage}' stage")

    utils.validate_opts(stage=stage, stage_opts=preproc_opts)
    utils.generate_mrtrix_conf(global_opts=global_opts, runner=runner)

    # Load b2t table, querying if necessary
    df = io.load_participant_table(input_dir=input_dir, cfg=global_opts, logger=logger)
    if preproc_opts.query.participant is not None:
        df = io.query(df=df, query=preproc_opts.query.participant)

    dwi_df = df
    if preproc_opts.query.dwi is not None:
        dwi_df = io.query(df=df, query=preproc_opts.query.dwi)

    # Loop through remaining subjects after query
    output_dir = Path(output_dir)
    groupby_keys = io.valid_groupby(df=dwi_df, keys=["sub", "ses", "run"])
    for group_vals, group in tqdm(
        dwi_df.filter(
            (pl.col("suffix") == "dwi") & (pl.col("ext").is_in([".nii", ".nii.gz"]))
        ).group_by(groupby_keys)
    ):
        input_group = dict(
            zip([key.lstrip("ent__") for key in groupby_keys], group_vals)
        )

        # Outer loops - combined direction, inner loop - single direction
        logger.info(f"Processing {(uid := bids_path(**input_group))}")
        dir_outs: DefaultDict[str, list[Any]] = defaultdict(list)
        undistort_opts = preproc_opts.undistort.opts
        for idx, row in enumerate(group.iter_rows(named=True)):
            input_data = io.get_inputs(
                df=df,
                row=row,
                query_opts=preproc_opts.query,
                stage_opts=preproc_opts.undistort,
                stage=stage,
            )
            entities = {
                k: v for k, v in row.items() if k in ["sub", "ses", "run", "dir"]
            }
            bids = partial(bids_path, **entities)
            dwi = preprocess.denoise.denoise(
                **input_data["dwi"],
                denoise_opts=preproc_opts.denoise,
                bids=bids,
                output_fpath=output_dir / bids(datatype="dwi", directory=True),
                logger=logger,
            )

            dwi = preprocess.unring.degibbs(
                dwi=dwi, unring_opts=preproc_opts.unring, bids=bids, logger=logger
            )
            for key, val in (
                ("dwi", dwi or input_data["dwi"]["nii"]),
                ("bval", input_data["dwi"]["bval"]),
                ("bvec", input_data["dwi"]["bvec"]),
            ):
                dir_outs[key].append(val)

            if (
                isinstance(undistort_opts.topup, cfg_.preprocess.TopupConfig)
                and not undistort_opts.topup.skip
                and isinstance(undistort_opts.eddy, cfg_.preprocess.EddyConfig)
                and not undistort_opts.eddy.skip
            ):
                b0, pe_dir, pe_data = preprocess.dwi.get_phenc_data(
                    dwi=dwi,
                    bval=input_data["dwi"]["bval"],
                    bvec=input_data["dwi"]["bvec"],
                    json=input_data["dwi"]["json"],
                    idx=idx,
                    metadata_opts=preproc_opts.metadata,
                    bids=bids,
                    logger=logger,
                )
                for key, val in (("b0", b0), ("pe_data", pe_data), ("pe_dir", pe_dir)):
                    dir_outs[key].append(val)

        bids = partial(bids_path, **input_group)
        match preproc_opts.undistort.method.lower():
            case "topup":
                # Topup
                phenc, indices, topup = preprocess.topup.run_apply_topup(
                    **dir_outs,
                    topup_opts=undistort_opts.topup,
                    bids=bids,
                    output_dir=global_opts.work_dir,
                    logger=logger,
                )
                # Eddy
                dwi, bval, bvec = preprocess.eddy.run_eddy(
                    **dir_outs,
                    phenc=phenc,
                    indices=indices,
                    topup=topup,
                    eddy_opts=undistort_opts.eddy,
                    bids=bids,
                    working_dir=global_opts.work_dir,
                    output_dir=output_dir / bids(datatype="dwi", directory=True),
                    logger=logger,
                )
            case "fieldmap":
                # Mimic input_data dict for preprocessing
                if not input_data:  # type: ignore
                    raise ValueError("Input data is missing")
                fmap_data = {"dwi": {k: v for k, v in input_data["fmap"].items()}}
                entities = parse_bids_entities(fmap_data["dwi"]["nii"])
                entities = {
                    k: v
                    for k, v in entities.items()
                    if k in ["sub", "ses", "run", "dir"]
                }
                bids = partial(bids_path, **entities)
                fmap = preprocess.denoise.denoise(
                    **fmap_data["dwi"],
                    denoise_opts=preproc_opts.denoise,
                    bids=bids,
                    output_fpath=output_dir / bids(datatype="dwi", directory=True),
                    logger=logger,
                )
                fmap = preprocess.unring.degibbs(
                    dwi=fmap,
                    unring_opts=preproc_opts.unring,
                    bids=bids,
                    logger=logger,
                )
                for key, val in (
                    ("dwi", fmap),
                    ("bval", fmap_data["dwi"]["bval"]),
                    ("bvec", fmap_data["dwi"]["bvec"]),
                ):
                    dir_outs[key].append(val)

                if (
                    isinstance(undistort_opts.topup, cfg_.preprocess.TopupConfig)
                    and not undistort_opts.topup.skip
                    and isinstance(undistort_opts.eddy, cfg_.preprocess.EddyConfig)
                    and not undistort_opts.eddy.skip
                ):
                    b0, pe_dir, pe_data = preprocess.dwi.get_phenc_data(
                        dwi=fmap,
                        bval=input_data["fmap"]["bval"],
                        bvec=input_data["fmap"]["bvec"],
                        json=input_data["fmap"]["json"],
                        idx=len(dir_outs["dwi"]),
                        metadata_opts=preproc_opts.metadata,
                        bids=bids,
                        logger=logger,
                    )
                    for key, val in (
                        ("b0", b0),
                        ("pe_data", pe_data),
                        ("pe_dir", pe_dir),
                    ):
                        dir_outs[key].append(val)

                # Topup
                phenc, indices, topup = preprocess.topup.run_apply_topup(
                    **dir_outs,
                    topup_opts=undistort_opts.topup,
                    bids=bids,
                    output_dir=global_opts.work_dir,
                )
                if phenc is not None:
                    for key in dir_outs.keys():
                        dir_outs[key].pop()
                # Eddy
                dwi, bval, bvec = preprocess.eddy.run_eddy(
                    **dir_outs,
                    phenc=phenc,
                    indices=indices,
                    topup=topup,
                    eddy_opts=undistort_opts.eddy,
                    bids=bids,
                    working_dir=global_opts.work_dir,
                    output_dir=output_dir / bids(datatype="dwi", directory=True),
                )
            case "fugue":
                # For legacy datasets (single phase-encode + fieldmap)
                if input_data:  # type: ignore
                    raise ValueError("Input data is missing")
                dwi = None  # type: ignore[assignment]
                dwi, bval, bvec = preprocess.eddy.run_eddy(
                    **dir_outs,
                    phenc=None,
                    indices=None,
                    topup=None,
                    eddy_opts=undistort_opts.eddy,
                    bids=bids,
                    working_dir=global_opts.work_dir,
                    output_dir=output_dir / bids(datatype="dwi", directory=True),
                    logger=logger,
                )
                dwi = preprocess.fugue.run_fugue(
                    dwi=dwi or dir_outs["dwi"][0],
                    fmap=input_data["fmap"]["nii"],  # type: ignore
                    pe_dir=dir_outs["pe_dir"][0],
                    json=input_data["dwi"]["json"],  # type: ignore
                    fugue_opts=undistort_opts.fugue,
                    echo_spacing=str(preproc_opts.metadata.echo_spacing)
                    if preproc_opts.metadata.echo_spacing is not None
                    else None,
                    logger=logger,
                )
            case "eddymotion":
                dwi, bval, bvec = preprocess.eddymotion.eddymotion(
                    **dir_outs,
                    eddymotion_opts=undistort_opts.eddymotion,
                    seed=global_opts.seed_number,
                    bids=bids,
                    output_dir=global_opts.work_dir,
                    threads=global_opts.threads,
                    logger=logger,
                )

        # Ensure variables are bound
        if not input_data:  # type: ignore
            raise ValueError("Input data is missing")
        dwi = locals().get("dwi", input_data["dwi"]["nii"])
        bval = locals().get("bval", input_data["dwi"]["bval"])
        bvec = locals().get("bvec", input_data["dwi"]["bvec"])

        logger.info("Performing bias correction")
        dwi, mask = preprocess.biascorrect.biascorrect(
            dwi=dwi,
            bval=bval,
            bvec=bvec,
            biascorrect_opts=preproc_opts.biascorrect,
            bids=bids,
            output_dir=output_dir / bids(datatype="dwi", directory=True),
        )

        bval_fpath = output_dir / (
            bids(
                datatype="dwi",
                space="T1w",
                res="dwi",
                desc="preproc",
                suffix="dwi",
                ext=".bval",
                return_path=True,
            )
        )
        if not preproc_opts.registration.skip:
            ref_b0, transforms = preprocess.registration.register(
                t1w=input_data["t1w"]["nii"],
                t1w_mask=input_data["dwi"].get("mask"),
                dwi=dwi,
                bval=bval,
                bvec=bvec,
                mask=mask,
                reg_opts=preproc_opts.registration,
                bids=bids,
                working_dir=global_opts.work_dir,
                output_dir=output_dir / bids(datatype="dwi", directory=True),
                threads=global_opts.threads,
                logger=logger,
            )
            dwi, mask, bvec = preprocess.registration.apply_transform(
                dwi=dwi,
                bvec=bvec,
                ref_b0=ref_b0,
                transforms=transforms,
                t1w_mask=input_data["dwi"].get("mask"),
                mask=input_data["dwi"].get("mask"),
                bids=bids,
                working_dir=global_opts.work_dir,
                output_dir=output_dir / bids(datatype="dwi", directory=True),
                logger=logger,
            )
        else:
            bval_fpath = Path(str(bval_fpath).replace("space-T1w_", ""))
        shutil.copy2(bval, bval_fpath)
        dwi_lib.grad_check(nii=dwi, bvec=bvec, bval=bval_fpath, mask=mask)

        # Create JSON sidecar
        json_fpath = bval_fpath.with_suffix(".json")
        json_fpath.write_text(json.dumps(input_data["dwi"]["json"], indent=2))

        logger.info(f"Completed processing for {uid}")

    # Clean up workflow
    if not global_opts.work_keep:
        cleanup()

    # Print graph
    if global_opts.graph:
        if not isinstance(runner, GraphRunner):
            raise TypeError(f"Expected GraphRunner, runner is of type {type(runner)}")
        logger.info("Mermaid workflow graph")
        logger.info(runner.generate_mermaid())
