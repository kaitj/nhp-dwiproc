"""Utility functions specifically for working in the CLI."""

import json
from pathlib import Path
from typing import Any

import typer
import yaml


def _json_dict_callback(value: str | None) -> dict[str, str] | None:
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
