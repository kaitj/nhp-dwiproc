"""Application descriptor."""

from typing import Any

from bidsapp_helper.descriptor import BidsAppDescriptor


def generate_descriptor(cfg: dict[str, Any], out_fname: str) -> None:
    """Generator and save app descriptor."""
    descriptor = BidsAppDescriptor(
        app_name="nhp_dwiproc generated dataset",
        bids_version="1.9.0",
        app_version="0.1.0",
        repo_url="https://github.com/kaitj/nhp-dwiproc",
        author="Jason Kai",
        author_email="jason.kai@childmind.org",
    )

    descriptor.save(cfg["output_dir"] / out_fname)
