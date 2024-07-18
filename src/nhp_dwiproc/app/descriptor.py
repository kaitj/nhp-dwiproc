"""Application descriptor."""

import importlib.metadata as ilm
import pathlib as pl

from bidsapp_helper.descriptor import BidsAppDescriptor

from . import APP_NAME


def generate_descriptor(out_fpath: pl.Path) -> None:
    """Generator and save app descriptor."""
    descriptor = BidsAppDescriptor(
        app_name=f"{APP_NAME.replace('_', ' ')} generated dataset",
        bids_version="1.9.0",
        app_version=ilm.version("nhp_dwiproc"),
        repo_url="https://github.com/kaitj/nhp-dwiproc",
        author="Jason Kai",
        author_email="jason.kai@childmind.org",
    )
    descriptor.save(out_fpath)
