"""Pre-tractography participant processing (to compute FODs)."""

from logging import Logger
from typing import Any

from bids2table import BIDSTable
from tqdm import tqdm

from nhp_dwiproc.app import utils
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
    b2t = utils.io.load_b2t(cfg=cfg, logger=logger)

    # Filter b2t based on string query
    if cfg.get("participant.query"):
        b2t = b2t.loc[b2t.flat.query(cfg.get("participant.query", "")).index]

    # Loop through remaining subjects after query
    assert isinstance(b2t, BIDSTable)
    dwi_b2t = b2t
    if cfg.get("participant.query_dwi"):
        dwi_b2t = b2t.loc[b2t.flat.query(cfg["participant.query_dwi"]).index]

    assert isinstance(dwi_b2t, BIDSTable)
    groupby_keys = utils.io.valid_groupby(
        b2t=dwi_b2t, keys=["sub", "ses", "run", "space"]
    )
    for group_vals, group in tqdm(
        dwi_b2t.filter_multi(suffix="dwi", ext={"items": [".nii", ".nii.gz"]}).groupby(
            groupby_keys
        )
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
            logger.info(
                f"Processing {(uid := utils.bids_name(**input_kwargs['input_group']))}"
            )
            if cfg.get("participant.connectivity.atlas"):
                connectivity.generate_conn_matrix(**input_kwargs)
            else:
                connectivity.extract_tract(**input_kwargs)
            logger.info(f"Completed processing for {uid}")
