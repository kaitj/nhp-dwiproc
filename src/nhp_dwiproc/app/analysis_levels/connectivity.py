"""Connectivity (post reconstruction - tractography) stage-level."""

import logging
import shutil
from functools import partial
from pathlib import Path

import polars as pl
from niwrap import GraphRunner, LocalRunner, Runner
from niwrap_helper.bids import bids_path
from niwrap_helper.types import StrPath
from tqdm import tqdm

from nhp_dwiproc import utils
from nhp_dwiproc.workflow.diffusion import connectivity

from ...config.connectivity import ConnectivityConfig, ConnectomeConfig, TractMapConfig
from ...config.shared import GlobalOptsConfig


def run(
    input_dir: StrPath,
    output_dir: StrPath,
    conn_opts: ConnectivityConfig = ConnectivityConfig(),
    global_opts: GlobalOptsConfig = GlobalOptsConfig(),
    runner: Runner = LocalRunner(),
    logger: logging.Logger = logging.Logger(__name__),
) -> None:
    """Runner for connectivity analysis-level."""
    logger.info("Performing 'connectivity' stage")

    # Load df table, querying if necessary
    df = utils.io.load_participant_table(
        input_dir=input_dir, cfg=global_opts, logger=logger
    )
    if conn_opts.query.participant is not None:
        df = utils.io.query(df=df, query=conn_opts.query.participant)

    dwi_df = df
    if conn_opts.query.dwi is not None:
        dwi_df = utils.io.query(df=df, query=conn_opts.query.dwi)

    # Loop through remaining subjects after query
    groupby_keys = utils.io.valid_groupby(
        df=dwi_df, keys=["sub", "ses", "run", "space"]
    )
    for group_vals, group in tqdm(
        dwi_df.filter(
            (pl.col("suffix") == "dwi") & (pl.col("ext").is_in([".nii", ".nii.gz"]))
        ).group_by(groupby_keys)
    ):
        for row in group.iter_rows(named=True):
            input_data = utils.io.get_inputs(
                df=df,
                row=row,
                query_opts=conn_opts.query,
                stage_opts=conn_opts.opts,
                stage="connectivity",
            )
            input_group = dict(zip([key for key in groupby_keys], group_vals))

            # Perform processing
            uid = bids_path(**input_group)
            logger.info(f"Processing {uid}")
            bids = partial(bids_path, datatype="dwi", **input_group)
            output_fpath = Path(output_dir) / bids(directory=True)

            # Generate connectivity matrices
            if conn_opts.method == "connectome":
                if not isinstance(conn_opts.opts, ConnectomeConfig):
                    raise TypeError(
                        f"Expected ConnectomeConfig, got {type(conn_opts.opts)}"
                    )
                logger.info("Generating connectivity matrices")
                connectivity.generate_conn_matrix(
                    atlas_fpath=input_data["dwi"]["atlas"],
                    **input_data["dwi"]["tractography"],
                    search_radius=conn_opts.opts.radius,
                    output_fpath=output_fpath,
                    bids=bids,
                )
            # Perform tract extraction and optional surface mapping
            elif conn_opts.method == "tract":
                if not isinstance(conn_opts.opts, TractMapConfig):
                    raise TypeError(
                        f"Expected TractMapConfig, got {type(conn_opts.opts)}"
                    )
                logger.info("Extracting tract")
                tdi, hemi, label = connectivity.extract_tract(
                    **input_data["dwi"]["tractography"],
                    **input_data["anat"]["rois"],
                    voxel_size=conn_opts.opts.voxel_size,
                    output_fpath=output_fpath,
                    bids=bids,
                )

                if not input_data["anat"]["surfs"].get("inflated"):
                    logger.warning("Inflated surface not found; not mapping end points")
                else:
                    for surf_type in ["white", "pial", "inflated"]:
                        if len(surfs := input_data["anat"]["surfs"][surf_type]) > 1:
                            logger.warning(
                                f"More than 1 surface found: {surfs} - using "
                                "first surface"
                            )
                    logger.info("Mapping tract to surface")
                    connectivity.surface_map_tract(
                        tdi=tdi,
                        hemi=hemi,
                        label=label,
                        **input_data["anat"]["surfs"],
                        output_fpath=output_fpath,
                        bids=bids,
                    )
            logger.info(f"Completed processing for {uid}")

    # Clean up workflow
    if not global_opts.work_keep:
        shutil.rmtree(
            runner.base.data_dir if isinstance(runner, GraphRunner) else runner.data_dir
        )

    # Print graph
    if global_opts.graph:
        if not isinstance(runner, GraphRunner):
            raise TypeError(f"Expected GraphRunner, runner is of type {type(runner)}")
        logger.info("Mermaid workflow graph")
        logger.info(runner.generate_mermaid())
