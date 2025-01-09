"""Helper functions for dealing with metadata."""

from logging import Logger
from typing import Any


def phase_encode_dir(
    idx: int, dwi_json: dict[str, Any], cfg: dict[str, Any], logger: Logger, **kwargs
) -> str:
    """Check phase encoding direction - set if able / necessary."""
    if pe_dirs := cfg.get("participant.preprocess.metadata.pe_dirs"):
        logger.warning("Setting 'PhaseEncodingDirection'")
        dwi_json["PhaseEncodingDirection"] = pe_dirs[idx]
    elif "PhaseEncodingDirection" not in dwi_json:
        if "PhaseEncodingAxis" in dwi_json:
            logger.warning("Assuming 'PhaseEncodingDirection' from 'PhaseEncodingAxis'")
            dwi_json["PhaseEncodingDirection"] = dwi_json["PhaseEncodingAxis"]
        else:
            raise ValueError("'PhaseEncodingDirection' not found and cannot be assumed")

    return dwi_json["PhaseEncodingDirection"]


def echo_spacing(
    dwi_json: dict[str, Any], cfg: dict[str, Any], logger: Logger, **kwargs
) -> float:
    """Check echo spacing - set if provided."""
    if echo_spacing := cfg.get("participant.preprocess.metadata.echo_spacing"):
        logger.info("Using provided echo spacing")
        dwi_json["EffectiveEchoSpacing"] = float(echo_spacing)
    elif "EffectiveEchoSpacing" not in dwi_json:
        if "EstimatedEffectiveEchoSpacing" in dwi_json:
            logger.warning(
                "Assuming 'EffectiveEchoSpacing' from 'EstimatedEffectiveEchoSpacing'"
            )
            dwi_json["EffectiveEchoSpacing"] = dwi_json["EstimatedEffectiveEchoSpacing"]
        else:
            raise ValueError("Unable to assume 'EffectiveEchoSpacing'")

    return dwi_json["EffectiveEchoSpacing"]
