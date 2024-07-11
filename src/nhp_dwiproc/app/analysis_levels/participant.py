"""Runners for different analysis-levels."""

from argparse import Namespace
from logging import Logger

from bids2table import bids2table
from tqdm import tqdm

from .. import utils


def run(args: Namespace, logger: Logger) -> None:
    """Runner for participant-level analysis."""
    index_path = utils.check_index_path(args=args)

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
    for _, row in tqdm(
        b2t.filter_multi(
            space="T1w", suffix="dwi", ext={"items": [".nii", ".nii.gz"]}
        ).flat.iterrows()
    ):
        entities = utils.unique_entities(row)
        wf_inputs = utils.get_inputs(b2t=b2t, entities=entities)

        # Add something here that collects subject response functions
