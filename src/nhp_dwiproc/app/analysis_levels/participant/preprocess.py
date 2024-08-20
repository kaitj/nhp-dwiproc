"""Preprocessing of participants."""

from logging import Logger
from typing import Any

from bids2table import BIDSTable
from tqdm import tqdm

from nhp_dwiproc.app import utils
from nhp_dwiproc.workflow.diffusion.preprocess import denoise


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for preprocessing-level analysis."""
    logger.info("Preprocess analysis-level")
    b2t = utils.load_b2t(cfg=cfg, logger=logger)

    # Filter b2t based on string query
    if cfg["participant.query"]:
        assert isinstance(b2t, BIDSTable)
        b2t = b2t.loc[b2t.flat.query(cfg["participant.query"]).index]

    # Loop through remaining subjects after query
    assert isinstance(b2t, BIDSTable)
    for _, row in tqdm(
        b2t.filter_multi(
            space="T1w", suffix="dwi", ext={"items": [".nii", ".nii.gz"]}
        ).flat.iterrows()
    ):
        entities = utils.unique_entities(row)
        input_kwargs: dict[str, Any] = {
            "input_data": (
                input_data := utils.get_inputs(
                    b2t=b2t,
                    entities=entities,
                    atlas=None,
                )
            ),
            "cfg": cfg,
            "logger": logger,
        }

        # Perform processing
        logger.info(f"Processing {(uid := utils.bids_name(**input_data['entities']))}")
        dwi = denoise.denoise(**input_kwargs)
        logger.info(f"Completed processing for {uid}")
