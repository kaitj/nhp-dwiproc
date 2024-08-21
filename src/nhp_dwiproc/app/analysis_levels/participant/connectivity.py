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
    b2t = utils.load_b2t(cfg=cfg, logger=logger)

    # Filter b2t based on string query
    if cfg["participant.query"]:
        b2t = b2t.loc[b2t.flat.query(cfg["participant.query"]).index]

    # Loop through remaining subjects after query
    assert isinstance(b2t, BIDSTable)
    for _, row in tqdm(
        b2t.filter_multi(
            space="T1w", suffix="dwi", ext={"items": [".nii", ".nii.gz"]}
        ).flat.iterrows()
    ):
        input_kwargs: dict[str, Any] = {
            "input_data": utils.get_inputs(
                b2t=b2t,
                row=row,
                atlas=cfg["participant.connectivity.atlas"],
            ),
            "input_group": row[["sub", "ses", "run"]].to_dict(),
            "cfg": cfg,
            "logger": logger,
        }

        # Perform processing
        logger.info(
            f"Processing {(uid := utils.bids_name(**input_kwargs['input_group']))}"
        )
        connectivity.generate_conn_matrix(**input_kwargs)
        logger.info(f"Completed processing for {uid}")
