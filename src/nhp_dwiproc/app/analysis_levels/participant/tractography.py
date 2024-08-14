"""Pre-tractography participant processing (to compute FODs)."""

from functools import partial
from logging import Logger
from typing import Any

from bids2table import BIDSEntities, BIDSTable
from tqdm import tqdm

from ....workflow.diffusion import reconst, tractography
from ... import utils


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for tractography-level analysis."""
    logger.info("Tractography analysis-level")
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
            "bids": (
                bids := partial(
                    BIDSEntities.from_dict(input_data["entities"]).with_update,
                    datatype="dwi",
                )
            ),
            "cfg": cfg,
            "logger": logger,
        }

        # Perform processing
        logger.info(f"Processing {bids().to_path().name}")
        reconst.compute_dti(**input_kwargs)
        fods = reconst.compute_fods(**input_kwargs)
        tractography.generate_tractography(fod=fods, **input_kwargs)
        logger.info(f"Completed processing for {bids().to_path().name}")
