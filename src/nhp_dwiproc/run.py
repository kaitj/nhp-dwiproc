#!/usr/bin/env python
"""Main entrypoint of code."""

import logging
import os
import shutil
from typing import Any

import yaml
from styxdefs import DefaultRunner, set_global_runner
from styxdocker import DockerRunner
from styxsingularity import SingularityRunner

from . import app


def _set_runner_logger(cfg: dict[str, Any]) -> logging.Logger:
    """Set runner (defaults to local)."""
    if (runner := cfg["opt.runner"]) == "Docker":
        set_global_runner(DockerRunner(data_dir=cfg["opt.working_dir"]))
        logger = logging.getLogger(DockerRunner.logger_name)
        logger.info("Using Docker runner for processing")
    elif runner in ["Singularity", "Apptainer"]:
        if not cfg["opt.containers"]:
            raise ValueError(
                """Container config not provided ('--container-config')\n
            See https://github.com/kaitj/nhp-dwiproc/blob/main/src/nhp_dwiproc/app/resources/containers.yaml
            for an example."""
            )
        with open(cfg["opt.containers"], "r") as container_config:
            images = yaml.safe_load(container_config)
        set_global_runner(
            SingularityRunner(images=images, data_dir=cfg["opt.working_dir"])
        )
        logger = logging.getLogger(SingularityRunner.logger_name)
        logger.info("Using Singularity / Apptainer runner for processing")
    else:
        DefaultRunner(data_dir=cfg["opt.containers"])
        logger = logging.getLogger(DefaultRunner.logger_name)

    return logger


def main() -> None:
    """Application."""
    # Initialize app and parse arguments
    cfg = app.parser().parse_args()

    # Run workflow
    logger = _set_runner_logger(cfg=cfg)
    logger.info("Running NHP DWIProc v0.1.0")
    match cfg["analysis_level"]:
        case "index":
            app.analysis_levels.index.run(cfg=cfg, logger=logger)
        case "participant":
            app.analysis_levels.participant.run(cfg=cfg, logger=logger)
            app.generate_descriptor(cfg=cfg, out_fname="dataset_description.json")

    # Clean up working directory (removal of hard-coded 'styx_tmp' is workaround)
    if cfg["opt.working_dir"]:
        shutil.rmtree(cfg["opt.working_dir"])
    elif os.path.exists("styx_tmp"):
        shutil.rmtree("styx_tmp")
    else:
        logger.warning("Did not clean up working directory")


if __name__ == "__main__":
    main()
