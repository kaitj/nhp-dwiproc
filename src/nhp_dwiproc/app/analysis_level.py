"""Runners for different analysis-levels."""

import pathlib as pl
from argparse import Namespace
from logging import Logger

from bids2table import bids2table

from . import utils


def _check_index_path(args: Namespace) -> pl.Path:
    """Helper to check for index path."""
    if args.index_path is None:
        index_path = args.bids_dir / "index.b2t"
    index_path = args.index_path

    return index_path


def index(args: Namespace, logger: Logger) -> None:
    """Runner for index-level analysis."""
    index_path = _check_index_path(args=args)
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


def participant(args: Namespace, logger: Logger) -> None:
    """Runner for participant-level analysis."""
    index_path = _check_index_path(args=args)

    if index_path.exists():
        logger.info("Using existing bids2table index")
        b2t = bids2table(
            root=args.bids_dir, index_path=index_path, workers=args.threads
        )
    else:
        logger.info("Indexing bids dataset...")
        b2t = bids2table(
            root=args.bids_dir,
            persistent=False,
            workers=args.threads,
        )
        logger.warning(
            "Index created, but not saved - please run 'index' level analysis to save."
        )

    # Filter b2t based on string query
    if args.participant_query:
        b2t = b2t.loc[b2t.flat.query(args.participant_query).index]

    # Run for each unique combination of DWI entities
    for _, row in b2t.filter_multi(
        space="T1w", suffix="dwi", ext={"items": [".nii", ".nii.gz"]}
    ).flat.iterrows():
        entities = utils.unique_entities(row)
        wf_inputs = utils.get_inputs(b2t=b2t, entities=entities)
