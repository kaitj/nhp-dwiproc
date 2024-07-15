"""Pre-tractography participant processing (to compute FODs)."""

from argparse import Namespace
from functools import partial
from logging import Logger

import yaml
from bids2table import BIDSEntities, BIDSTable, bids2table
from styxdefs import set_global_runner
from styxdocker import DockerRunner
from styxsingularity import SingularityRunner
from tqdm import tqdm

from ...workflow.diffusion import reconst, tractography
from .. import utils


def _set_runner(args: Namespace, logger: Logger) -> None:
    """Set runner (defaults to local)."""
    if args.runner == "Docker":
        logger.info("Using Docker runner for processing")
        set_global_runner(DockerRunner())
    elif args.runner in ["Singularity", "Apptainer"]:
        if not args.container_config:
            raise ValueError(
                """Config not provided - please provide using '--container-config' \n
            See https://github.com/kaitj/nhp-dwiproc/blob/main/src/nhp_dwiproc/app/resources/images.yaml
            for an example."""
            )
        logger.info("Using Singularity / Apptainer runner for processing.")
        with open(args.container_config, "r") as container_config:
            images = yaml.safe_load(container_config)
        set_global_runner(SingularityRunner(images=images))


def run(args: Namespace, logger: Logger) -> None:
    """Runner for participant-level analysis."""
    _set_runner(args=args, logger=logger)
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

        fods = reconst.compute_fods(
            input_data=input_data, bids=bids, args=args, logger=logger
        )
        tractography.generate_tractography(
            input_data=input_data, fod=fods, bids=bids, args=args, logger=logger
        )

        logger.info(f"Completed processing for {bids().to_path().name}")