"""Utility functions for working with configs.

Todo:
  - Method for writing final config
"""

from collections.abc import Sequence
from dataclasses import fields, is_dataclass, replace
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, TypeVar

import yaml

T = TypeVar("T", bound=object)


@lru_cache
def load_config_file(file: str | Path) -> dict[str, Any]:
    """Load provided values from configuration file.

    Args:
        file: Path to config file.

    Returns:
        A dictionary of the config.
    """
    if (file := Path(file)).suffix not in [".yaml", ".yml"]:
        raise ValueError("Only YAML-based configuration files are currently supported.")

    with open(file, "r") as cfg_file:
        return yaml.safe_load(cfg_file)


def build_config(
    cfg_class: type[T],
    cfg_key: str,
    cfg_file: Path | None = None,
    ctx_params: dict[str, Any] | None = None,
    ignore_params: str | Sequence[str] = "config",
    include_only: str | Sequence[str] | None = None,
    cli_map: dict[str, str] | None = None,
    dynamic_method_map: dict[str, dict[Any, type]] | None = None,
) -> T:
    """Merge defaults, config file and CLI arguments into dataclass.

    Args:
        cfg_class: Config dataclass to build.
        cfg_key: Config key to grab from / set.
        cfg_file: Configuration file path, if provided.
        ctx_params: Command line parameters passed, if provided.
        ignore_params: Command line keys to ignore.
        include_only: Command line keys to filter for, if provided.
        cli_map: Dictionary mapping cli params to nested keys.
        dynamic_method_map: Dictionary methods mapping to configs for dynamic switching.

    Returns:
        Merged dataclass configuration.
    """

    def _replace_nested(dc_instance: T, update_dict: dict[str, Any]) -> T:
        """Recursively replace fields in a dataclass, preserving the nestedness.

        Args:
            dc_instance: Nested dataclass instance.
            update_dict: Dictionary of values to replace current values with.

        Returns:
            Updated dataclass instance.

        Raises:
            ValueError: If invalid Enum value
        """
        if not is_dataclass(dc_instance):
            raise TypeError(f"{dc_instance} must be a dataclass instance.")
        updates: dict[str, Any] = {}
        for field in fields(dc_instance):
            if field.name not in update_dict:
                continue
            new_value = update_dict[field.name]
            cur_value = getattr(dc_instance, field.name)

            # Recursively handle nested dataclasses
            if is_dataclass(cur_value) and isinstance(new_value, dict):
                new_value = _replace_nested(cur_value, new_value)  # type: ignore[arg-type]
            # Handle Enum fields
            elif isinstance(cur_value, Enum):
                enum_cls = type(cur_value)
                if not isinstance(new_value, enum_cls):
                    try:
                        new_value = enum_cls(new_value)
                    except ValueError:
                        raise ValueError(
                            f"Invalid value '{new_value}' for '{field.name}'"
                            f"Valid values: {[e.value for e in enum_cls]}"
                        )

            updates[field.name] = new_value
        return replace(dc_instance, **updates) if updates else dc_instance  # type: ignore[type-var]

    def _filter_ctx_params(
        ctx_params: dict[str, Any],
        ignore_params: Sequence[str] | set[str],
        include_only: Sequence[str] | set[str] | None = None,
    ) -> dict[str, Any]:
        """Filter parameters.

        Args:
            ctx_params: Dictionary of CLI parameters.
            ignore_params: Keys to ignore.
            include_only: Keys to filter for, if provided.

        Returns:
            Filtered dictionary for replacing dataclass fields.
        """
        ignore = set(ignore_params)
        include = None if include_only is None else set(include_only)

        return {
            k: v
            for k, v in ctx_params.items()
            if v not in (None, ())
            and k not in ignore
            and (include is None or k in include)
        }

    def _map_cli_to_nested(
        cli_opts: dict[str, Any], mapping: dict[str, str]
    ) -> dict[str, Any]:
        """Convert flat CLI params into nested dict based on mapping.

        Args:
            cli_opts: Dictionary of cli parameters.
            mapping: Dictionary mapping cli keys to nested keys.

        Returns:
            Dictionary with updated values from CLI.
        """
        nested_updates: dict[str, Any] = {}
        # Apply CLI options
        for cli_key, nested_path in mapping.items():
            value = cli_opts.get(cli_key)
            if value is None:
                continue

            target = nested_updates
            path = nested_path.split(".")
            for part in path[:-1]:
                target = target.setdefault(part, {})
            target[path[-1]] = cli_opts[cli_key]

        # Carry forward unmapped CLI options
        for k, v in cli_opts.items():
            if v is not None and k not in mapping:
                nested_updates[k] = v
        return nested_updates

    def _apply_dynamic(dc_instance: T, method_map: dict[str, dict[Any, type]]) -> T:
        """Apply method config dynamically based on selected method.

        Note: Creates a new instance of a config if generated.

        Args:
            dc_instance: Nested dataclass instance.
            method_map: Mapping of method to method config.

        Returns:
            Updated dataclass instance with associated options.

        Raises:
            ValueError: If method config does not exist.
        """
        for path, mapping in method_map.items():
            parts = path.split(".")
            parent = dc_instance
            for p in parts[:-1]:
                parent = getattr(parent, p)

            method_field = parts[-1]
            method_val = getattr(parent, method_field)
            if method_val not in mapping:
                raise ValueError(f"Unknown method '{method_val}' for '{path}'")
            target_cls = mapping[method_val]

            if not is_dataclass(target_cls):
                raise TypeError(
                    f"Dynamic mapping for '{method_val}' must be a dataclass class"
                )

            current_opts = getattr(parent, "opts", None)
            if current_opts is None:
                setattr(parent, "opts", target_cls())
            elif not isinstance(current_opts, target_cls):
                # Preserve overlapping fields
                new_values = {
                    f.name: getattr(current_opts, f.name)
                    for f in fields(target_cls)
                    if hasattr(current_opts, f.name)
                }
                setattr(parent, "opts", target_cls(**new_values))
        return dc_instance

    if not is_dataclass(cfg_class):
        raise ValueError(f"{cfg_class} must be a dataclass")

    # 1. Initialize defaults
    opts: T = cfg_class()

    # Load config file
    cfg = load_config_file(cfg_file) if cfg_file is not None else {}
    file_opts = cfg.get(cfg_key, {}) if cfg_file else {}

    # 2. Overwrite default values with config.
    if file_opts:
        opts = _replace_nested(opts, file_opts)

    # 3. Dynamically substitution (due to config)
    if dynamic_method_map:
        opts = _apply_dynamic(opts, dynamic_method_map)

    # 4. Load CLI
    if ctx_params:
        cli_opts = _filter_ctx_params(ctx_params, set(ignore_params), include_only)
        nested_cli = _map_cli_to_nested(cli_opts, cli_map) if cli_map else {}
        opts = _replace_nested(opts, nested_cli)

    # 5. Dynamic substitution (due to CLI)
    if dynamic_method_map:
        opts = _apply_dynamic(opts, dynamic_method_map)

    # 6. Reload config
    if file_opts:
        opts = _replace_nested(opts, file_opts)

    # 7. Reload CLI
    if ctx_params:
        opts = _replace_nested(opts, nested_cli if cli_map else cli_opts)

    return opts


def map_param(prefix: str, replace_with: str, vars_dict: dict) -> dict:
    """Map values to a config key.

    Args:
        prefix: Parameter value to map.
        replace_with: Replacement to map to config.
        vars_dict: Mapping of parameters and their values.

    Returns:
        Dictionary mapping input parameters to config keys.
    """
    return {
        k: k.replace(prefix, replace_with) for k in vars_dict if k.startswith(prefix)
    }
