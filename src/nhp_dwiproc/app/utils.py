"""Utility functions for application."""

import importlib.metadata as ilm
import logging
import pathlib as pl
import shutil
from functools import partial
from typing import Any

import pandas as pd
import yaml
from bids2table import BIDSTable
from styxdefs import (
    LocalRunner,
    OutputPathType,
    Runner,
    set_global_runner,
)
from styxdocker import DockerRunner
from styxgraph import GraphRunner
from styxsingularity import SingularityRunner

APP_NAME = "nhp_dwiproc"


def check_index_path(cfg: dict[str, Any]) -> pl.Path:
    """Helper to check for index path."""
    return (
        index_fpath
        if (index_fpath := cfg["opt.index_path"])
        else cfg["bids_dir"] / "index.b2t"
    )


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
    else:
        # Find relevant BIDs components of file path
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


def initialize(cfg: dict[str, Any]) -> tuple[logging.Logger, Runner]:
    """Set runner (defaults to local)."""
    # Create working directory if it doesn't already exist
    if cfg["opt.working_dir"]:
        cfg["opt.working_dir"].mkdir(parents=True, exist_ok=True)

    if cfg["opt.runner"] == "Docker":
        runner = GraphRunner(DockerRunner(data_dir=cfg["opt.working_dir"]))
        logger = logging.getLogger(DockerRunner.logger_name)
        logger.info("Using Docker runner for processing")
    elif cfg["opt.runner"] in ["Singularity", "Apptainer"]:
        if not cfg["opt.containers"]:
            raise ValueError(
                """Container config not provided ('--container-config')\n
            See https://github.com/kaitj/nhp-dwiproc/blob/main/src/nhp_dwiproc/app/resources/containers.yaml
            for an example."""
            )
        with open(cfg["opt.containers"], "r") as container_config:
            images = yaml.safe_load(container_config)
        runner = GraphRunner(
            SingularityRunner(images=images, data_dir=cfg["opt.working_dir"])
        )
        logger = logging.getLogger(SingularityRunner.logger_name)
        logger.info("Using Singularity / Apptainer runner for processing")
    else:
        runner = GraphRunner(LocalRunner(data_dir=cfg["opt.containers"]))
        logger = logging.getLogger(LocalRunner.logger_name)
    set_global_runner(runner)

    logger.info(f"Running {APP_NAME} v{ilm.version(APP_NAME)}")
    return logger, runner
