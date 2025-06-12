"""Pre-tractography participant processing (to compute FODs)."""

from functools import partial
from logging import Logger
from typing import Any

import niwrap_helper
import polars as pl
from tqdm import tqdm

import nhp_dwiproc.utils as utils
from nhp_dwiproc.lib import dwi as dwi_lib
from nhp_dwiproc.workflow.diffusion import reconst, tractography


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for tractography-level analysis."""
    # Load BIDSTable, querying if necessary
    logger.info("Tractography analysis-level")
    df = utils.io.load_participant_table(cfg=cfg, logger=logger)
    if cfg.get("participant.query") is not None:
        df = utils.io.query(df=df, query=cfg["participant.query"])
    if not isinstance(df, pl.DataFrame):
        raise TypeError(f"Expected polars.DataFrame, but got {type(df).__name__}")

    dwi_df = df
    if cfg.get("participant.query_dwi") is not None:
        dwi_df = utils.io.query(df=df, query=cfg["participant.query_dwi"])
    if not isinstance(dwi_df, pl.DataFrame):
        raise TypeError(f"Expected polars.DataFrame, but got {type(dwi_df).__name__}")

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
            input_data = utils.io.get_inputs(df=df, row=row, cfg=cfg)
            input_group = dict(zip([key for key in groupby_keys], group_vals))

            # Perform processing
            uid = niwrap_helper.bids_path(**input_group)
            logger.info(f"Processing {uid}")
            bids = partial(niwrap_helper.bids_path, datatype="dwi", **input_group)
            output_fpath = cfg["output_dir"] / bids(directory=True)
            dwi_lib.grad_check(**input_data["dwi"])

            logger.info("Performing tensor fitting and generating maps")
            reconst.compute_dti(
                **input_data["dwi"], output_fpath=output_fpath, bids=bids
            )

            logger.info(
                "Computing response function and fibre orientation distribution"
            )
            fods = reconst.compute_fods(
                **input_data["dwi"],
                single_shell=cfg["participant.tractography.single_shell"],
                shells=cfg.get("participant.tractography.shells", None),
                lmax=cfg.get("participant.tractography.lmax", None),
                bids=bids,
            )

            logger.info("Generating tractography and computing weights")
            tractography.generate_tractography(
                dwi_5tt=input_data["dwi"].get("5tt", None),
                method=cfg["participant.tractography.method"],
                fod=fods,
                steps=cfg.get("participant.tractography.steps", None),
                cutoff=cfg.get("participant.tractography.cutoff", None),
                streamlines=cfg["participant.tractography.streamlines"],
                backtrack=cfg["participant.tractography.act.backtrack"],
                nocrop_gmwmi=cfg["participant.tractography.act.nocrop_gmwmi"],
                output_fpath=output_fpath,
                bids=bids,
            )

            logger.info(f"Completed processing for {uid}")
