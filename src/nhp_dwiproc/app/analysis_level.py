"""Runners for different analysis-levels."""

from argparse import Namespace
from logging import Logger

from bids2table import bids2table


def index(args: Namespace, logger: Logger) -> None:
    """Runner for index-level analysis."""
    if args.index_path is None:
        index_path = args.bids_dir / "index.b2t"
    index_path = args.index_path

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
