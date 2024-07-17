"""Index analysis-level."""

from argparse import Namespace
from logging import Logger

from bids2table import bids2table

from .. import utils


def run(args: Namespace, logger: Logger) -> None:
    """Runner for index-level analysis."""
    logger.info("Index analysis-level")
    index_path = utils.check_index_path(args=args)
    if index_path.exists() and not args.index_overwrite:
        logger.info("Index already exists - not overwriting")
    else:
        logger.info("Indexing bids dataset...")
        bids2table(
            root=args.bids_dir,
            index_path=index_path,
            overwrite=args.index_overwrite,
            persistent=True,
            workers=args.threads,
        )
