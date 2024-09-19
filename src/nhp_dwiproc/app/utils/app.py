"""Utility functions related to the application."""

import importlib.metadata as ilm
import logging
import pathlib as pl
import re
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
            if not cfg.get("opt.containers"):
                raise ValueError(
                    """Container config not provided ('--container-config')\n
                See https://github.com/HumanBrainED/nhp-dwiproc/blob/main/src/nhp_dwiproc/app/resources/containers.yaml
                for an example."""
                )
            with open(cfg["opt.containers"], "r") as container_config:
                images = yaml.safe_load(container_config)
            runner = SingularityRunner(images=images)
        case _:
            runner = LocalRunner()

    # Redirect intermediate files if option selected
    if cfg["opt.keep_tmp"]:
        cfg["opt.working_dir"] = cfg["output_dir"].joinpath(
            f'working/{datetime.now().isoformat(timespec="seconds").replace(":", "-")}'
        )
    runner.data_dir = cfg["opt.working_dir"]
    runner.environ = {"MRTRIX_RNG_SEED": str(cfg["opt.seed_num"])}
    set_global_runner(GraphRunner(runner))

    logger = logging.getLogger(runner.logger_name)
    logger.info(f"Running {utils.APP_NAME} v{ilm.version(utils.APP_NAME)}")
    return logger, get_global_runner()


def validate_cfg(cfg: dict[str, Any]) -> None:
    """Helper function to validate input arguments if necessary."""
    # Check that participant query only contains general entities
    allowed_keys = {"sub", "ses"}
    if cfg.get("participant.query"):
        query_keys = re.findall(r"\b(\w+)=", cfg["participant.query"])
        invalid_keys = [key for key in query_keys if key not in allowed_keys]
        assert (
            not invalid_keys
        ), "Only 'sub', 'ses', 'run' accepted for participant query"

    match cfg["analysis_level"]:
        case "index":
            pass
        case "preprocess":
            # Check PE direction
            valid_dirs = ("i", "i-", "j", "j-", "k", "k-")
            if pe_dirs := cfg.get("participant.preprocess.metadata.pe_dirs"):
                if len(pe_dirs) > 2:
                    raise ValueError("More than 2 phase encode directions provided")
                assert all(
                    pe_dir in valid_dirs for pe_dir in pe_dirs
                ), "Invalid PE direction provided"

            # Validate TOPUP config
            topup_cfg = cfg.get("participant.preprocess.topup.config", "b02b0_macaque")
            if topup_cfg not in ["b02b0", "b02b0_macaque", "b02b0_marmoset"]:
                if not pl.Path(topup_cfg).exists():
                    logging.error("No topup configuration found")
                    raise FileNotFoundError()
                topup_cfg = str(topup_cfg).rstrip(".cnf")
            cfg["participant.preprocess.topup.config"] = (
                pl.Path(__file__).parent.parent
                / "resources"
                / "topup"
                / f"{topup_cfg}.cnf"
            )
        case "tractography":
            pass
        case "connectivity":
            pass


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
