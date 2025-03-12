"""Index analysis-level."""

from logging import Logger
from pathlib import Path
from typing import Any

from bids2table import bids2table


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for index-level analysis."""
    logger.info("Index analysis-level")
    index_path: Path = cfg.get("opt.index_path", cfg["bids_dir"] / "index.b2t")
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
