"""Utilities directly related to application runtime."""

import importlib.metadata as ilm
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from styxdefs import LocalRunner, Runner, get_global_runner, set_global_runner
from styxdocker import DockerRunner
from styxgraph import GraphRunner
from styxsingularity import SingularityRunner

from nhp_dwiproc import APP_LOCATION, APP_NAME


def initialize(cfg: dict[str, Any]) -> tuple[logging.Logger, Runner]:
    """Initialize runner and logging setup based on configuration."""
    # Ensure working directory exists
    if cfg["opt.working_dir"]:
        cfg["opt.working_dir"].mkdir(parents=True, exist_ok=True)

    # Select appropriate runner
    match cfg["opt.runner"].lower():
        case "docker":
            runner = DockerRunner()
        case "singularity" | "apptainer":
            if not (container_cfg := cfg.get("opt.containers")):
                raise ValueError(
                    "Container config not provided ('--container-config')\n"
                    "See example: https://github.com/HumanBrainED/nhp-dwiproc/blob/main/src/nhp_dwiproc/app/resources/containers.yaml"
                )
            runner = SingularityRunner(images=yaml.safe_load(container_cfg.read_text()))
        case _:
            runner = LocalRunner()

    # Redirect intermediate files if saving
    if cfg["opt.keep_tmp"]:
        cfg["opt.working_dir"] = (
            cfg["output_dir"]
            / "working"
            / f"{datetime.now().isoformat(timespec='seconds').replace(':', '-')}"
        )

    runner.data_dir = cfg["opt.working_dir"]
    runner.environ = {
        "MRTRIX_NTHREADS": str(cfg.get("opt.threads")),
        "MRTRIX_RNG_SEED": str(cfg.get("opt.seed_num")),
    }
    set_global_runner(GraphRunner(runner))

    logger = logging.getLogger(runner.logger_name)
    logger.info(f"Running {APP_NAME} v{ilm.version(APP_NAME)}")
    return logger, get_global_runner()


def validate_cfg(cfg: dict[str, Any]) -> None:
    """Validate configuration file."""
    # Pariticipant query keys
    if query := cfg.get("participant.query"):
        invalid_keys = [
            key for key in re.findall(r"\b(\w+)=", query) if key not in {"sub", "ses"}
        ]
        if invalid_keys:
            raise ValueError("Only 'sub' and 'ses' are valid participant query keys")

    match cfg["analysis_level"].lower():
        case "index" | "tractography" | "connectivity":
            pass
        case "preprocess":
            # Validate phase-encode directions.
            if pe_dirs := cfg.get("participant.preprocess.metadata.pe_dirs"):
                if len(pe_dirs) > 2:
                    raise ValueError("More than 2 phase encode directions provided")
                if any(
                    pe_dir not in {"i", "i-", "j", "j-", "k", "k-"}
                    for pe_dir in pe_dirs
                ):
                    raise ValueError("Invalid phase-encode direction provided")

            # Validate TOPUP config
            topup_cfg = cfg.get("participant.preprocess.topup.config", "b02b0_macaque")
            if topup_cfg not in {"b02b0", "b02b0_macaque", "b02b0_marmoset"}:
                if not Path(topup_cfg).exists():
                    raise FileNotFoundError("TOPUP configuration not found")
                topup_cfg = str(topup_cfg).rstrip(".cnf")
            cfg["participant.preprocess.topup.config"] = (
                APP_LOCATION / "resources" / "topup" / f"{topup_cfg}.cnf"
            )
        case _:
            raise ValueError("Invalid analysis level provided")
