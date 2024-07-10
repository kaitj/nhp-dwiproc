"""Utility functions for applicaiton."""

from functools import partial
from typing import Any

import pandas as pd
from bids2table import BIDSTable


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
            .file_path
        },
    }

    return wf_inputs
