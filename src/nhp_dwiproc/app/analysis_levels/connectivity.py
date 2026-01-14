"""Connectivity (post reconstruction - tractography) stage-level."""

import logging
from functools import partial
from pathlib import Path

import polars as pl
from niwrap import GraphRunner, LocalRunner, Runner
from niwrap_helper import bids_path, cleanup
from niwrap_helper.types import StrPath
from tqdm import tqdm

from nhp_dwiproc import config as cfg_
from nhp_dwiproc.app import io, utils
from nhp_dwiproc.app.workflow import connectivity


def run(
    input_dir: StrPath,
    output_dir: StrPath,
    conn_opts: cfg_.ConnectivityConfig = cfg_.ConnectivityConfig(),
    global_opts: cfg_.GlobalOptsConfig = cfg_.GlobalOptsConfig(),
    runner: Runner = LocalRunner(),
    logger: logging.Logger = logging.Logger(__name__),
) -> None:
    """Runner for connectivity analysis-level.

    Args:
        input_dir: Input dataset directory path.
        output_dir: Output directory.
        conn_opts: Connectivity stage config options.
        global_opts: Global config options.
        runner: StyxRunner used.
        logger: Logger object.

    Returns:
        None

    Raises:
        TypeError if configs of an unexpected type.
    """
    stage = "connectivity"
    logger.info(f"Performing '{stage}' stage")

    utils.validate_opts(stage=stage, stage_opts=conn_opts)
    utils.generate_mrtrix_conf(global_opts=global_opts, runner=runner)

    # Load b2t table, querying if necessary
    df = io.load_participant_table(input_dir=input_dir, cfg=global_opts, logger=logger)
    if conn_opts.query.participant is not None:
        df = io.query(df=df, query=conn_opts.query.participant)

    dwi_df = df
    if conn_opts.query.dwi is not None:
        dwi_df = io.query(df=df, query=conn_opts.query.dwi)

    # Loop through remaining subjects after query
    groupby_keys = io.valid_groupby(df=dwi_df, keys=["sub", "ses", "run", "space"])
    for group_vals, group in tqdm(
        dwi_df.filter(
            (pl.col("suffix") == "tractography") & (pl.col("ext") == ".tck")
        ).group_by(groupby_keys)
    ):
        for row in group.iter_rows(named=True):
            input_data = io.get_inputs(
                df=df,
                row=row,
                query_opts=conn_opts.query,
                stage_opts=conn_opts.opts,
                stage=stage,
            )
            input_group = dict(zip([key for key in groupby_keys], group_vals))

            # Perform processing
            uid = bids_path(**input_group)
            logger.info(f"Processing {uid}")
            bids = partial(bids_path, datatype="dwi", **input_group)
            output_fpath = Path(output_dir) / bids(directory=True)

            # Generate connectivity matrices
            if conn_opts.method == "connectome":
                if not isinstance(conn_opts.opts, cfg_.connectivity.ConnectomeConfig):
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
                if not isinstance(conn_opts.opts, cfg_.connectivity.TractMapConfig):
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
        cleanup()

    # Print graph
    if global_opts.graph:
        if not isinstance(runner, GraphRunner):
            raise TypeError(f"Expected GraphRunner, runner is of type {type(runner)}")
        logger.info("Mermaid workflow graph")
        logger.info(runner.generate_mermaid())
