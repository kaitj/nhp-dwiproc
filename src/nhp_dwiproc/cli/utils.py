"""Utility functions specifically for working in the CLI."""

import json
import logging
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import typer
import yaml

from nhp_dwiproc import config as cfg

LOG_LEVELS = [logging.INFO, logging.DEBUG]


def setup_logging(verbose: int) -> int:
    """Convert verbose count to logging level."""
    return (
        LOG_LEVELS[min(verbose, len(LOG_LEVELS)) - 1]
        if verbose > 0
        else logging.CRITICAL + 1
    )


def build_global_opts(
    ctx_params: dict,
    cfg_file: Path | None,
    prefix: str = "opts_",
) -> cfg.GlobalOptsConfig:
    """Build global options configuration."""
    local_vars = {k: v for k, v in ctx_params.items() if k.startswith(prefix)}
    mapper = partial(cfg.utils.map_param, vars_dict=local_vars)

    opt_map = mapper(prefix, "")
    opt_map.update(
        {f"{prefix}runner": "runner.name", f"{prefix}images": "runner.images"}
    )
    builder = partial(cfg.utils.build_config, ctx_params=ctx_params, cfg_file=cfg_file)
    return builder(
        cfg_class=cfg.GlobalOptsConfig,
        cfg_key="opts",
        include_only=list(opt_map.keys()),
        cli_map=opt_map,
    )


def finalize_stage(
    ctx: SimpleNamespace, logger: logging.Logger, include_descriptor: bool = True
) -> None:
    """Finalization steps for each stage."""
    logger.setLevel(ctx.log_level)
    logger.debug(f"Stage options:\n\n{_namespace_to_yaml(obj=ctx)}")

    if include_descriptor:
        cfg.utils.generate_descriptor(
            app_name=ctx.app,
            version=ctx.version,
            out_fpath=ctx.output_dir / "dataset_description.json",
        )


def json_dict_callback(value: str | None) -> dict[str, str] | None:
    """Callback helper to convert CLI images to dictionary.

    Args:
        value: String value to attempt to convert if provided

    Returns:
        Dictionary object representing JSON string.

    Raises:
        JSONDecodeError: if invalid JSON string.
    """
    try:
        return json.loads(value) if value is not None else None
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"Invalid JSON: {e}")


def _namespace_to_yaml(obj: Any) -> str:
    """Convert namespace / object to YAML-safe string.

    Args:
        obj: Object to convert

    Returns:
        YAML-safe string
    """

    def _convert(o: Any) -> Any:
        if hasattr(o, "__dict__"):
            return {k: _convert(v) for k, v in vars(o).items()}
        elif isinstance(o, (list, tuple, set)):
            return [_convert(v) for v in o]  # tuples/sets → lists for YAML
        elif isinstance(o, Path):
            return str(o)
        else:
            return o

    return yaml.safe_dump(_convert(obj), sort_keys=False)
