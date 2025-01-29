"""Index analysis-level."""

from logging import Logger
from typing import Any

from bids2table import bids2table

import nhp_dwiproc.utils as utils


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for index-level analysis."""
    logger.info("Index analysis-level")
    index_path = utils.io.check_index_path(cfg=cfg)
    if index_path.exists() and not cfg["index.overwrite"]:
        logger.info("Index already exists - not overwriting")
    else:
        logger.info("Indexing bids dataset...")
        bids2table(
            root=cfg["bids_dir"],
            index_path=index_path,
            overwrite=cfg["index.overwrite"],
            persistent=True,
            workers=cfg["opt.threads"],
        )
