"""Reconstruction (DTI, tractography) processing."""

import logging
from functools import partial
from pathlib import Path

import polars as pl
from niwrap import GraphRunner, LocalRunner, Runner
from niwrap_helper import bids_path, cleanup
from niwrap_helper.types import StrPath
from tqdm import tqdm

from ... import config as cfg_
from .. import io, utils
from ..lib import dwi as dwi_lib
from ..workflow.reconstruction import reconst, tractography


def run(
    input_dir: StrPath,
    output_dir: StrPath,
    recon_opts: cfg_.ReconstructionConfig = cfg_.ReconstructionConfig(),
    global_opts: cfg_.GlobalOptsConfig = cfg_.GlobalOptsConfig(),
    runner: Runner = LocalRunner(),
    logger: logging.Logger = logging.Logger(__name__),
) -> None:
    """Runner for reconstruction analysis-level.

    Args:
        input_dir: Input dataset directory path.
        output_dir: Output directory.
        recon_opts: Reconstruction stage config options.
        global_opts: Global config options.
        runner: StyxRunner used.
        logger: Logger object.

    Returns:
        None

    Raises:
        TypeError if configs of an unexpected type.
    """
    stage = "reconstruction"
    logger.info(f"Performing '{stage}' stage")

    utils.validate_opts(stage=stage, stage_opts=recon_opts)
    utils.generate_mrtrix_conf(global_opts=global_opts, runner=runner)

    # Load b2t table, querying if necessary
    df = io.load_participant_table(input_dir=input_dir, cfg=global_opts, logger=logger)
    if recon_opts.query.participant is not None:
        df = io.query(df=df, query=recon_opts.query.participant)

    dwi_df = df
    if recon_opts.query.dwi is not None:
        dwi_df = io.query(df=df, query=recon_opts.query.dwi)

    # Loop through remaining subjects after query
    groupby_keys = io.valid_groupby(df=dwi_df, keys=["sub", "ses", "run", "space"])
    for group_vals, group in tqdm(
        dwi_df.filter(
            (pl.col("suffix") == "dwi") & (pl.col("ext").is_in([".nii", ".nii.gz"]))
        ).group_by(groupby_keys)
    ):
        for row in group.iter_rows(named=True):
            input_data = io.get_inputs(
                df=df,
                row=row,
                query_opts=recon_opts.query,
                stage_opts=None,  # No stage opts for IO
                stage=stage,
            )
            input_group = dict(zip([key for key in groupby_keys], group_vals))

            # Perform processing
            uid = bids_path(**input_group)
            logger.info(f"Processing {uid}")
            bids = partial(bids_path, datatype="dwi", **input_group)
            output_fpath = Path(output_dir) / bids(directory=True)
            dwi_lib.grad_check(**input_data["dwi"])

            # TODO: Implement TensorConfig for skipping.
            logger.info("Performing tensor fitting and generating maps")
            reconst.compute_dti(
                **input_data["dwi"], output_fpath=output_fpath, bids=bids
            )

            if not recon_opts.tractography.skip:
                logger.info(
                    "Computing response function and fibre orientation distribution"
                )
                fods = reconst.compute_fods(
                    **input_data["dwi"],
                    single_shell=recon_opts.tractography.single_shell,
                    shells=recon_opts.tractography.shells,  # type: ignore[arg-type]
                    lmax=recon_opts.tractography.lmax,
                    bids=bids,
                    logger=logger,
                )

                logger.info("Generating tractography and computing weights")
                tractography.generate_tractography(
                    dwi_5tt=input_data["dwi"].get("5tt", None),
                    method=recon_opts.tractography.method,
                    fod=fods,
                    steps=recon_opts.tractography.steps,
                    cutoff=recon_opts.tractography.cutoff,
                    streamlines=recon_opts.tractography.streamlines,
                    maxlength=recon_opts.tractography.max_length,
                    backtrack=recon_opts.tractography.opts.backtrack
                    if isinstance(
                        recon_opts.tractography.opts,
                        cfg_.reconstruction.TractographyACTConfig,
                    )
                    else False,
                    nocrop_gmwmi=recon_opts.tractography.opts.no_crop_gmwmi
                    if isinstance(
                        recon_opts.tractography.opts,
                        cfg_.reconstruction.TractographyACTConfig,
                    )
                    else False,
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
