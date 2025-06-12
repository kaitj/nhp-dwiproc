"""Index analysis-level."""

from logging import Logger
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq
from niwrap_helper.bids import get_bids_table


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for index-level analysis."""
    logger.info("Index analysis-level")
    index_path: Path = cfg.get("opt.index_path", cfg["bids_dir"] / ".index.parquet")
    if index_path.exists() and not cfg["index.overwrite"]:
        logger.info("Index already exists - not overwriting")
    else:
        logger.info("Indexing bids dataset...")
        table = get_bids_table(dataset_dir=cfg["bids_dir"], index=index_path)
        pq.write_table(table, index_path)
