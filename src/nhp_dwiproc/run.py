#!/usr/bin/env python
"""Main entrypoint of code."""

import importlib.metadata as ilm
import logging
from argparse import Namespace

import yaml
from styxdefs import DefaultRunner, set_global_runner
from styxdocker import DockerRunner
from styxsingularity import SingularityRunner

from . import app


def _set_runner_logger(args: Namespace) -> logging.Logger:
    """Set runner (defaults to local)."""
    if args.runner == "Docker":
        set_global_runner(DockerRunner(data_dir=args.working_dir))
        logger = logging.getLogger(DockerRunner.logger_name)
        logger.info("Using Docker runner for processing")
    elif args.runner in ["Singularity", "Apptainer"]:
        if not args.container_config:
            raise ValueError(
                """Config not provided - please provide using '--container-config' \n
            See https://github.com/kaitj/nhp-dwiproc/blob/main/src/nhp_dwiproc/app/resources/images.yaml
            for an example."""
            )
        with open(args.container_config, "r") as container_config:
            images = yaml.safe_load(container_config)
        set_global_runner(SingularityRunner(images=images, data_dir=args.working_dir))
        logger = logging.getLogger(SingularityRunner.logger_name)
        logger.info("Using Singularity / Apptainer runner for processing")
    else:
        logger = logging.getLogger(DefaultRunner.logger_name)

    return logger


def main() -> None:
    """Application."""
    # Parse arguments
    args = app.parser().parse_args()

    logger = _set_runner_logger(args=args)
    logger.info(f"Running NHP DWIProc v{ilm.version('nhp_dwiproc')}")
    match args.analysis_level:
        case "index":
            app.analysis_levels.index.run(args=args, logger=logger)
        case "participant":
            app.analysis_levels.participant.run(args=args, logger=logger)
            app.pipeline_descriptor(args.output_dir / "pipeline_description.json")


if __name__ == "__main__":
    main()
