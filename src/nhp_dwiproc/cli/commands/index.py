"""Index stage command implementation."""

import logging
from functools import partial
from pathlib import Path

import typer
from niwrap_helper import setup_styx

from nhp_dwiproc import app
from nhp_dwiproc import config as cfg_
from nhp_dwiproc.cli import utils as cli_utils
from nhp_dwiproc.cli.utils import LOG_LEVELS


def command(
    ctx: typer.Context,
    opts_config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML-formatted configuration file. [default: "
        f"{cfg_.GlobalOptsConfig.config}]",
        exists=True,
        dir_okay=False,
        file_okay=True,
        resolve_path=True,
    ),
    opts_threads: int | None = typer.Option(
        None,
        "--threads",
        help=f"Number of threads to use [default: {cfg_.GlobalOptsConfig.threads}].",
    ),
    opts_index_path: Path | None = typer.Option(
        None,
        "--index-path",
        help="Path to read / write bids2table index. [default: "
        f"{cfg_.GlobalOptsConfig.index_path}]",
        writable=True,
    ),
    overwrite: bool | None = typer.Option(
        None,
        "--overwrite",
        help="Overwrite existing bids2table index. [default: "
        f"{cfg_.IndexConfig.overwrite}]",
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="Verbosity (-v, -vv, -vvv)."),
) -> None:
    """Index stage-level."""
    builder = partial(
        cfg_.utils.build_config, ctx_params=ctx.params, cfg_file=opts_config
    )
    # Global options
    ctx.obj.cfg.opt = cli_utils.build_global_opts(
        ctx_params=ctx.params, cfg_file=opts_config
    )
    # Index options
    ctx.obj.cfg.index = builder(
        cfg_class=cfg_.IndexConfig, cfg_key="index", include_only=["overwrite"]
    )
    # Verbosity
    ctx.obj.log_level = (
        LOG_LEVELS[min(verbose, len(LOG_LEVELS)) - 1]
        if verbose > 0
        else logging.CRITICAL + 1
    )
    # Setup stage
    logger, runner = setup_styx(runner="local")
    cli_utils.finalize_stage(ctx=ctx.obj, logger=logger)
    app.analysis_levels.index(
        input_dir=ctx.obj.cfg.input_dir,
        index_opts=ctx.obj.cfg.index,
        global_opts=ctx.obj.cfg.opt,
        runner=runner,
        logger=logger,
    )
