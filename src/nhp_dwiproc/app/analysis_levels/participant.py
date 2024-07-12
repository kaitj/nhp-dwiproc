"""Pre-tractography participant processing (to compute FODs)."""

from argparse import Namespace
from functools import partial
from logging import Logger

from bids2table import BIDSEntities, BIDSTable, bids2table
from tqdm import tqdm

from ...workflow.diffusion import reconst
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
        assert isinstance(b2t, BIDSTable)
        b2t = b2t.loc[b2t.flat.query(args.participant_query).index]

    # Loop through remaining subjects after query
    assert isinstance(b2t, BIDSTable)
    for _, row in tqdm(
        b2t.filter_multi(
            space="T1w", suffix="dwi", ext={"items": [".nii", ".nii.gz"]}
        ).flat.iterrows()
    ):
        entities = utils.unique_entities(row)
        input_data = utils.get_inputs(b2t=b2t, entities=entities)
        bids = partial(BIDSEntities.from_dict(input_data["entities"]).with_update)

        logger.info(f"Processing {bids().to_path().name}")

        fods = reconst.compute_subj_fods(
            input_data=input_data, bids=bids, args=args, logger=logger
        )
