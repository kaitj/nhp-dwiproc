"""IO related functions for application."""

import logging
import pathlib as pl
import shutil
from functools import partial
from typing import Any

import pandas as pd
from bids2table import BIDSTable, bids2table
from styxdefs import OutputPathType

from nhp_dwiproc.app import utils


def check_index_path(cfg: dict[str, Any]) -> pl.Path:
    """Helper to check for index path."""
    return (
        index_fpath
        if (index_fpath := cfg["opt.index_path"])
        else cfg["bids_dir"] / "index.b2t"
    )


def load_b2t(cfg: dict[str, Any], logger: logging.Logger) -> BIDSTable:
    """Handle loading of bids2table."""
    index_path = check_index_path(cfg=cfg)

    if index_path.exists():
        logger.info("Existing bids2table found")
        if overwrite := cfg["opt.overwrite"]:
            logger.info("Overwriting existing table")
        b2t = bids2table(
            root=cfg["bids_dir"],
            index_path=index_path,
            workers=cfg["opt.threads"],
            overwrite=overwrite,
        )
    else:
        logger.info("Indexing bids dataset...")
        b2t = bids2table(
            root=cfg["bids_dir"], persistent=False, workers=cfg["opt.threads"]
        )
        logger.warning(
            "Index created, but not saved - please run 'index' level analysis to save"
        )

    # Flatten entities s.t. extra_ents can be filtered
    extra_entities = pd.json_normalize(b2t["ent__extra_entities"]).set_index(b2t.index)
    b2t = pd.concat([b2t, extra_entities.add_prefix("ent__")], axis=1)

    return b2t.drop(columns="ent__extra_entities")


def get_inputs(
    b2t: BIDSTable, row: pd.Series, atlas: str | None = None
) -> dict[str, Any]:
    """Helper to grab relevant inputs for workflow."""
    fpath = partial(utils.bids_name, return_path=True, **row.dropna().to_dict())

    wf_inputs = {
        "dwi": {
            "nii": fpath(),
            "bval": fpath(ext=".bval"),
            "bvec": fpath(ext=".bvec"),
            "mask": fpath(suffix="mask"),
            "json": fpath(ext=".json"),
        },
        "t1w": {"nii": fpath(datatype="anat", suffix="T1w")},
        "atlas": {
            "nii": fpath(space="T1w", seg=atlas, suffix="dseg") if atlas else None
        },
        "tractography": {
            "tck": fpath(method="iFOD2", suffix="tractography", ext=".tck"),
            "weights": fpath(method="SIFT2", suffix="tckWeights", ext=".txt"),
        },
    }

    return wf_inputs


def save(
    files: OutputPathType | list[OutputPathType],
    out_dir: pl.Path,
) -> None:
    """Helper function to save file to disk."""
    # Recursively call save for each file in list
    if isinstance(files, list):
        for file in files:
            save(file, out_dir=out_dir)
    else:
        # Find relevant BIDs components of file path
        out_fpath = None
        for idx, fpath_part in enumerate(parts := files.parts):
            if "sub-" in fpath_part:
                out_fpath = out_dir.joinpath(*parts[idx:])
                break
        else:
            raise ValueError(
                "Unable to find relevant file path components to save file."
            )

        out_fpath.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(files, out_dir.joinpath(out_fpath))
