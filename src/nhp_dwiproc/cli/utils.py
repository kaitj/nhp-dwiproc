"""Utility functions specifically for working in the CLI."""

import json

import typer


def _json_dict_callback(value: str | None) -> dict[str, str] | None:
    try:
        return json.loads(value) if value is not None else None
    except json.JSONDecodeError as e:
        raise typer.BadParameter(f"Invalid JSON: {e}")
