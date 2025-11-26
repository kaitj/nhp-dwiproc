"""Index stage-level."""

import logging
from pathlib import Path

import pyarrow.parquet as pq
from niwrap_helper import cleanup, get_bids_table
from niwrap_helper.types import LocalRunner, StrPath

from nhp_dwiproc import config as cfg


def run(
    input_dir: StrPath,
    index_opts: cfg.IndexConfig = cfg.IndexConfig(),
    global_opts: cfg.GlobalOptsConfig = cfg.GlobalOptsConfig(),
    runner: LocalRunner = LocalRunner(),
    logger: logging.Logger = logging.Logger(__name__),
) -> None:
    """Runner for index-level analysis.

    Args:
        input_dir: Path to dataset directory to index.
        index_opts: Index stage options.
        global_opts: Application options shared across different stages.
        runner: Runner used.
        logger: Logger object.

    Returns:
        None
    """
    logger.info("Performing 'index' stage")
    index_path = global_opts.index_path or f"{input_dir}/.index.parquet"
    if Path(index_path).exists() and not index_opts.overwrite:
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
    # Clean up workflow
    if not global_opts.work_keep and runner.data_dir.exists():
        cleanup()
