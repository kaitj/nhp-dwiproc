"""Utilities directly related to application runtime."""

import logging
import re
from datetime import datetime
from pathlib import Path

from niwrap import GraphRunner
from niwrap_helper import setup_styx
from niwrap_helper.types import BaseRunner, DockerRunner, SingularityRunner

from .. import config as cfg
from . import resources


def initialize(
    output_dir: Path, global_opts: cfg.GlobalOptsConfig
) -> tuple[logging.Logger, GraphRunner | BaseRunner]:
    """Initialize application runners.

    Args:
        output_dir: Output directory.
        global_opts: Global configuration options.

    Returns:
        A 2-tuple, where first is the logger object and the second is the StyxRunner.

    """
    # Redirect working directory if necessary and ensure it exists
    if global_opts.work_keep:
        global_opts.work_dir = (
            output_dir
            / "working"
            / f"{datetime.now().isoformat(timespec='seconds').replace(':', '-')}"
        )
    Path(global_opts.work_dir).mkdir(parents=True, exist_ok=True)

    # Setup appropriate runner
    logger, runner = setup_styx(
        runner=global_opts.runner.name,
        image_map=global_opts.runner.images,
        graph_runner=global_opts.graph,
    )
    runner_base = runner.base if isinstance(runner, GraphRunner) else runner
    runner_base.environ = {
        "MRTRIX_CONFIGFILE": (
            f"{runner_base.data_dir}/{runner_base.uid}_cfgs/.mrtrix.conf"
        ),
        "MRTRIX_NTHREADS": str(global_opts.threads),
        "MRTRIX_RNG_SEED": str(global_opts.seed_number),
    }
    return logger, runner


def generate_mrtrix_conf(
    global_opts: cfg.GlobalOptsConfig, runner: GraphRunner | BaseRunner
) -> None:
    """Write temporary mrtrix configuration file.

    Args:
        global_opts: Global configuration options.
        runner: StyxRunner used.

    Raises:
        TypeError: If runner type does not match expected.
    """
    runner_base = runner.base if isinstance(runner, GraphRunner) else runner
    cfg_path = runner_base.data_dir / f"{runner_base.uid}_cfgs" / ".mrtrix.conf"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    with cfg_path.open("w") as f:
        f.write(f"BZeroThreshold: {global_opts.b0_thresh}")

    match global_opts.runner.name.lower():
        case "docker" | "podman":
            if not isinstance(runner_base, DockerRunner):
                raise TypeError(f"Expected DockerRunner, got {type(runner_base)}")
            runner_base.docker_extra_args.extend(
                [
                    "--mount",
                    f"type=bind,source={cfg_path},target={cfg_path},readonly",
                ]
            )
        case "singularity" | "apptainer":
            if not isinstance(runner_base, SingularityRunner):
                raise TypeError(f"Expected SingularityRunner, got {type(runner_base)}")
            runner_base.singularity_extra_args.extend(
                ["--bind", f"{cfg_path}:{cfg_path}:ro"]
            )
        case _:
            pass


def validate_opts(
    stage: str,
    query_opts: cfg.QueryConfig | None = None,
    stage_opts: cfg.PreprocessConfig
    | cfg.ReconstructionConfig
    | cfg.ConnectivityConfig
    | None = None,
) -> None:
    """Validate configuration file.

    Args:
        stage: Current processing stage.
        query_opts: Query configuration options.
        stage_opts: Stage-specific configuration options.

    Raises:
        FileNotFoundError: If configuration file paths not found.
        TypeError: If config type is incorrect for stage.
        ValueError: If invalid keys encountered during querying, more than number of
            expected values encountered, or invalid values are encountered in stage
            options.
    """
    # Pariticipant query keys
    if query_opts and query_opts.participant is not None:
        invalid_keys = [
            key
            for key in re.findall(r"\b(\w+)=", query_opts.participant)
            if key not in {"sub", "ses"}
        ]
        if invalid_keys:
            raise ValueError("Only 'sub' and 'ses' are valid participant query keys")

    match stage.lower():
        case "index" | "reconstruction" | "connectivity":
            pass
        case "preprocess":
            if not isinstance(stage_opts, cfg.PreprocessConfig):
                raise TypeError(f"Expected PreprocessConfig, got {type(stage_opts)}")
            # Validate phase-encode directions.
            if stage_opts.metadata.pe_dirs is not None:
                if len(stage_opts.metadata.pe_dirs) > 2:
                    raise ValueError("More than 2 phase encode directions provided")
                if any(
                    pe_dir not in {"i", "i-", "j", "j-", "k", "k-"}
                    for pe_dir in stage_opts.metadata.pe_dirs
                ):
                    raise ValueError("Invalid phase-encode direction provided")
            # Validate TOPUP config
            if not isinstance(
                stage_opts.undistort.opts.topup, cfg.preprocess.TopupConfig
            ):
                raise TypeError(
                    f"Expected TopupConfig, got {type(cfg.preprocess.TopupConfig)}"
                )
            if stage_opts.undistort.opts.topup.config not in {
                "b02b0",
                "b02b0_macaque",
                "b02b0_marmoset",
            }:
                topup_cfg = str(stage_opts.undistort.opts.topup.config).rstrip(".cnf")
                stage_opts.undistort.opts.topup.config = f"{topup_cfg}.cnf"
            else:
                stage_opts.undistort.opts.topup.config = str(
                    Path(resources.__file__).parent
                    / "topup"
                    / f"{stage_opts.undistort.opts.topup.config}.cnf"
                )
            # Check to make sure configuration exists
            if not Path(stage_opts.undistort.opts.topup.config).exists():
                raise FileNotFoundError("TOPUP configuration not found")
