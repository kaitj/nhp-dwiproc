"""Index analysis-level."""

import logging
from pathlib import Path

import pyarrow.parquet as pq
from niwrap_helper.bids import get_bids_table
from niwrap_helper.types import StrPath

from ...config import shared


def run(
    input_dir: StrPath,
    index_opts: shared.IndexConfig = shared.IndexConfig(),
    global_opts: shared.GlobalOptsConfig = shared.GlobalOptsConfig(),
    logger: logging.Logger = logging.Logger(__name__),
) -> None:
    """Runner for index-level analysis.

    Args:
        input_dir: Path to dataset directory to index.
        index_opts: Index stage options.
        global_opts: Application options shared across different stages.
        logger: Logger object.

    Returns:
        None
    """
    logger.info("Performing 'index' stage")
    input_dir = Path(input_dir)
    index_path = global_opts.index_path or input_dir / ".index.parquet"
    if index_path.exists() and not index_opts.overwrite:
        logger.info("Index already exists - not overwriting")
    else:
        logger.info("Indexing dataset with bids2table...")
        table = get_bids_table(
            dataset_dir=input_dir,
            b2t_index=index_path,
            max_workers=global_opts.threads,
            verbose=logger.level < logging.CRITICAL + 1,
        )
        pq.write_table(table, index_path)
