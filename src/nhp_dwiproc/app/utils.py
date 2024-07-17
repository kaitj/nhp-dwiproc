"""Utility functions for applicaiton."""

import pathlib as pl
import shutil
from argparse import Namespace
from functools import partial
from typing import Any

import pandas as pd
from bids2table import BIDSTable
from styxdefs import OutputPathType


def check_index_path(args: Namespace) -> pl.Path:
    """Helper to check for index path."""
    return args.index_path if args.index_path else args.bids_dir / "index.b2t"


def unique_entities(row: pd.Series) -> dict[str, Any]:
    """Function to check for unique sub / ses / run entities."""
    return {
        key: value
        for key, value in row.items()
        if key in ["sub", "ses", "run"] and pd.notna(value)
    }


def get_inputs(b2t: BIDSTable, entities: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Helper to grab relevant inputs for workflow."""
    dwi_filter = partial(b2t.filter_multi, space="T1w", suffix="dwi", **entities)

    wf_inputs = {
        "dwi": {
            "nii": dwi_filter(ext={"items": [".nii", ".nii.gz"]})
            .flat.iloc[0]
            .file_path,
            "bval": dwi_filter(ext=".bval").flat.iloc[0].file_path,
            "bvec": dwi_filter(ext=".bvec").flat.iloc[0].file_path,
            "mask": dwi_filter(suffix="mask", ext={"items": [".nii", ".nii.gz"]})
            .flat.iloc[0]
            .file_path,
        },
        "t1w": {
            "nii": b2t.filter_multi(
                suffix="T1w", ext={"items": [".nii", ".nii.gz"]}, **entities
            )
            .flat.iloc[0]
            .file_path,
        },
        "entities": {**entities},
    }

    return wf_inputs


def save(files: OutputPathType | list[OutputPathType], out_dir: pl.Path) -> None:
    """Helper function to save file to disk."""
    # Recursively call save for each file in list
    if isinstance(files, list):
        for file in files:
            save(file, out_dir=out_dir)

    # Find relevant BIDs components of file path
    assert isinstance(files, OutputPathType)
    for idx, fpath_part in enumerate(parts := files.parts):
        if "sub-" in fpath_part:
            out_fpath = out_dir.joinpath(*parts[idx:])
            break
    else:
        raise ValueError("Unable to find relevant file path components to save file.")

    out_fpath.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(files, out_dir.joinpath(out_fpath))
