"""Utility functions for application."""

import importlib.metadata as ilm
import logging
import pathlib as pl
import shutil
from datetime import datetime
from functools import partial
from typing import Any

import pandas as pd
import yaml
from bids2table import BIDSTable, bids2table
from styxdefs import (
    LocalRunner,
    OutputPathType,
    Runner,
    get_global_runner,
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

    return b2t


def unique_entities(row: pd.Series) -> dict[str, Any]:
    """Function to check for unique sub / ses / run entities."""
    return {
        key: value
        for key, value in row.items()
        if key in ["sub", "ses", "run"] and pd.notna(value)
    }


def get_inputs(
    b2t: BIDSTable, entities: dict[str, Any], atlas: str | None
) -> dict[str, dict[str, Any]]:
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
        "atlas": {
            "nii": b2t.filter_multi(
                datatype="dwi",
                space="T1w",
                suffix="dseg",
                ext={"items": [".nii", ".nii.gz"]},
            )
            .filter("extra_entities", {"seg": atlas})
            .flat.iloc[0]
            .file_path
            if atlas
            else None
        },
        "tractography": {
            "tck": b2t.filter_multi(
                suffix="tractography",
                ext=".tck",
                **entities,
            )
            .filter("extra_entities", {"method": "iFOD2"})
            .flat.iloc[0]
            .file_path,
            "weights": b2t.filter_multi(
                suffix="tckWeights",
                ext=".txt",
                **entities,
            )
            .filter("extra_entities", {"method": "SIFT2"})
            .flat.iloc[0]
            .file_path,
        },
        "entities": {**entities},
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


def initialize(cfg: dict[str, Any]) -> tuple[logging.Logger, Runner]:
    """Set runner (defaults to local)."""
    # Create working directory if it doesn't already exist
    if cfg["opt.working_dir"]:
        cfg["opt.working_dir"].mkdir(parents=True, exist_ok=True)

    match cfg["opt.runner"]:
        case "Docker":
            runner = DockerRunner()
        case "Singularity" | "Apptainer":
            if not cfg["opt.containers"]:
                raise ValueError(
                    """Container config not provided ('--container-config')\n
                See https://github.com/kaitj/nhp-dwiproc/blob/main/src/nhp_dwiproc/app/resources/containers.yaml
                for an example."""
                )
            with open(cfg["opt.containers"], "r") as container_config:
                images = yaml.safe_load(container_config)
            runner = SingularityRunner(images=images)
        case _:
            runner = LocalRunner()

    # Finish configuring runner - if keeping temp, redirect runner's output
    runner.data_dir = (
        cfg["output_dir"].joinpath(
            f'working/{datetime.now().isoformat(timespec="seconds").replace(":", "-")}'
        )
        if cfg["opt.keep_tmp"]
        else cfg["opt.working_dir"]
    )
    runner.environ = {"MRTRIX_RNG_SEED": str(cfg["opt.seed_num"])}
    set_global_runner(GraphRunner(runner))

    logger = logging.getLogger(runner.logger_name)
    logger.info(f"Running {APP_NAME} v{ilm.version(APP_NAME)}")
    return logger, get_global_runner()
