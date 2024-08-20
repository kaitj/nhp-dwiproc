"""Application descriptor."""

import importlib.metadata as ilm
from typing import Any

from bidsapp_helper.descriptor import BidsAppDescriptor

from .utils import APP_NAME


def generate_descriptor(cfg: dict[str, Any], out_fname: str) -> None:
    """Generator and save app descriptor."""
    descriptor = BidsAppDescriptor(
        app_name=(
            f"{APP_NAME} generated dataset - {cfg['analysis_level']} analysis-level"
        ),
        bids_version="1.9.0",
        app_version=ilm.version(APP_NAME),
        repo_url="https://github.com/kaitj/nhp-dwiproc",
        author="Jason Kai",
        author_email="jason.kai@childmind.org",
    )

    descriptor.save(cfg["output_dir"] / out_fname)
