"""Pre-tractography participant processing (to compute FODs)."""

from logging import Logger
from typing import Any

from bids2table import BIDSTable
from tqdm import tqdm

from nhp_dwiproc import utils
from nhp_dwiproc.workflow.diffusion import connectivity


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for connectivity analysis-level."""
    logger.info("Connectivity analysis-level")
    if cfg.get("participant.connectivity.atlas") and (
        cfg.get("participant.connectivity.query_surf")
        or cfg.get("participant.connectivity.query_include")
        or cfg.get("participant.connectivity.query_exclude")
        or cfg.get("participant.connectivity.query_truncate")
    ):
        raise ValueError("Only one of atlas or ROIs should be provided")

    # Load BIDSTable, querying if necessary
    b2t = utils.io.load_b2t(cfg=cfg, logger=logger)
    if cfg.get("participant.query"):
        b2t = b2t.loc[b2t.flat.query(cfg.get("participant.query", "")).index]
    if not isinstance(b2t, BIDSTable):
        raise TypeError(f"Loaded table of type {type(b2t)} instead of BIDSTable")

    # Loop through remaining subjects after query
    dwi_b2t = b2t
    if cfg.get("participant.query_dwi"):
        dwi_b2t = b2t.loc[b2t.flat.query(cfg["participant.query_dwi"]).index]
    if not isinstance(dwi_b2t, BIDSTable):
        raise TypeError(f"Queried table of type {type(dwi_b2t)} instead of BIDSTable")

    # assert isinstance(dwi_b2t, BIDSTable)
    groupby_keys = utils.io.valid_groupby(
        b2t=dwi_b2t, keys=["sub", "ses", "run", "space"]
    )
    for group_vals, group in tqdm(
        dwi_b2t.filter_multi(suffix="tractography", ext=".tck").groupby(groupby_keys)
    ):
        for _, row in group.ent.iterrows():
            input_kwargs: dict[str, Any] = {
                "input_data": utils.io.get_inputs(
                    b2t=b2t,
                    row=row,
                    cfg=cfg,
                ),
                "input_group": dict(
                    zip([key.lstrip("ent__") for key in groupby_keys], group_vals)
                ),
                "cfg": cfg,
                "logger": logger,
            }

            # Perform processing
            uid = utils.io.bids_name(**input_kwargs["input_group"])
            logger.info(f"Processing {uid}")
            if cfg.get("participant.connectivity.atlas"):
                connectivity.generate_conn_matrix(**input_kwargs)
            elif cfg.get("participant.connectivity.query_tract"):
                connectivity.extract_tract(**input_kwargs)
            else:
                raise ValueError("No valid inputs provided for connectivity workflow")
            logger.info(f"Completed processing for {uid}")
