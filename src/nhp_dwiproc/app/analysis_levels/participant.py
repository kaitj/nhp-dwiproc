"""Pre-tractography participant processing (to compute FODs)."""

from functools import partial
from logging import Logger
from typing import Any

from bids2table import BIDSEntities, BIDSTable, bids2table
from tqdm import tqdm

from ...workflow.diffusion import reconst, tractography
from .. import utils


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for participant-level analysis."""
    logger.info("Participant analysis-level")
    index_path = utils.check_index_path(cfg=cfg)

    if index_path.exists():
        logger.info("Using existing bids2table index")
        b2t = bids2table(
            root=cfg["bids_dir"], index_path=index_path, workers=cfg["opt.threads"]
        )
    else:
        logger.info("Indexing bids dataset...")
        b2t = bids2table(
            root=cfg["bids_dir"],
            persistent=False,
            workers=cfg["opt.threads"],
        )
        logger.warning(
            "Index created, but not saved - please run 'index' level analysis to save"
        )

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
        input_data = utils.get_inputs(b2t=b2t, entities=entities)
        bids = partial(
            BIDSEntities.from_dict(input_data["entities"]).with_update, datatype="dwi"
        )

        logger.info(f"Processing {bids().to_path().name}")

        fods = reconst.compute_fods(
            input_data=input_data, bids=bids, cfg=cfg, logger=logger
        )
        tractography.generate_tractography(
            input_data=input_data, fod=fods, bids=bids, cfg=cfg, logger=logger
        )

        logger.info(f"Completed processing for {bids().to_path().name}")
