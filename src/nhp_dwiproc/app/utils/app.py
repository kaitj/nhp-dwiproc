"""Utility functions related to the application."""

import importlib.metadata as ilm
import logging
import pathlib as pl
from datetime import datetime
from typing import Any, Literal, overload

import yaml
from bids2table import BIDSEntities
from styxdefs import (
    LocalRunner,
    Runner,
    get_global_runner,
    set_global_runner,
)
from styxdocker import DockerRunner
from styxgraph import GraphRunner
from styxsingularity import SingularityRunner

from nhp_dwiproc.app import utils


def initialize(cfg: dict[str, Any]) -> tuple[logging.Logger, Runner]:
    """Set runner (defaults to local)."""
    # Create working directory if it doesn't already exist
    if cfg["opt.working_dir"]:
        cfg["opt.working_dir"].mkdir(parents=True, exist_ok=True)

    match cfg["opt.runner"]:
        case "Docker":
            runner = DockerRunner()
        case "Singularity" | "Apptainer":
            if not cfg["opt.containers"]:
                raise ValueError(
                    """Container config not provided ('--container-config')\n
                See https://github.com/kaitj/nhp-dwiproc/blob/main/src/nhp_dwiproc/app/resources/containers.yaml
                for an example."""
                )
            with open(cfg["opt.containers"], "r") as container_config:
                images = yaml.safe_load(container_config)
            runner = SingularityRunner(images=images)
        case _:
            runner = LocalRunner()

    # Finish configuring runner - if keeping temp, redirect runner's output
    runner.data_dir = (
        cfg["output_dir"].joinpath(
            f'working/{datetime.now().isoformat(timespec="seconds").replace(":", "-")}'
        )
        if cfg["opt.keep_tmp"]
        else cfg["opt.working_dir"]
    )
    runner.environ = {"MRTRIX_RNG_SEED": str(cfg["opt.seed_num"])}
    set_global_runner(GraphRunner(runner))

    logger = logging.getLogger(runner.logger_name)
    logger.info(f"Running {utils.APP_NAME} v{ilm.version(utils.APP_NAME)}")
    return logger, get_global_runner()


def validate_cfg(cfg: dict[str, Any]) -> None:
    """Helper function to validate input arguments if necessary."""
    match cfg["analysis_level"]:
        case "index":
            pass
        case "preprocess":
            # Check PE direction
            valid_dirs = ("i", "i-", "j", "j-", "k", "k-")
            pe_dirs = cfg.get("participant.preprocess.metadata.pe_dirs", [])
            if len(pe_dirs) > 2:
                raise ValueError("More than 2 phase encode directions provided")
            assert all(
                pe_dir in valid_dirs for pe_dir in pe_dirs
            ), "Invalid PE direction provided"
        case "tractography":
            ...
        case "connectivity":
            ...


@overload
def bids_name(
    directory: Literal[False], return_path: Literal[False], **entities
) -> str: ...


@overload
def bids_name(
    directory: Literal[False], return_path: Literal[True], **entities
) -> pl.Path: ...


@overload
def bids_name(
    directory: Literal[True], return_path: Literal[False], **entities
) -> pl.Path: ...


def bids_name(
    directory: bool = False, return_path: bool = False, **entities
) -> pl.Path | str:
    """Helper function to generate bids-esque name."""
    if return_path and directory:
        raise ValueError("Only one of 'directory' or 'return_path' can be True")

    name = BIDSEntities.from_dict(entities).to_path()
    if return_path:
        return name
    elif directory:
        return name.parent
    else:
        return name.name
