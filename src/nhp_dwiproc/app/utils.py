"""Utility functions for application."""

import importlib.metadata as ilm
import logging
import pathlib as pl
import shutil
from datetime import datetime
from functools import partial
from typing import Any, Literal, overload

import pandas as pd
import yaml
from bids2table import BIDSEntities, BIDSTable, bids2table
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

    # Flatten entities s.t. extra_ents can be filtered
    extra_entities = pd.json_normalize(b2t["ent__extra_entities"]).set_index(b2t.index)
    b2t = pd.concat([b2t, extra_entities.add_prefix("ent__")], axis=1)

    return b2t.drop(columns="ent__extra_entities")


def get_inputs(
    b2t: BIDSTable, row: pd.Series, atlas: str | None = None
) -> dict[str, Any]:
    """Helper to grab relevant inputs for workflow."""
    fpath = partial(bids_name, return_path=True, **row.dropna().to_dict())

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


@overload
def bids_name(
    directory: Literal[False], return_path: Literal[False], **entities
) -> str: ...


@overload
def bids_name(
    directory: Literal[False], return_path: Literal[True], **entities
) -> pl.Path: ...


@overload
def bids_name(
    directory: Literal[True], return_path: Literal[False], **entities
) -> pl.Path: ...


def bids_name(
    directory: bool = False, return_path: bool = False, **entities
) -> pl.Path | str:
    """Helper function to generate bids-esque name."""
    if return_path and directory:
        raise ValueError("Only one of 'directory' or 'return_path' can be True")

    name = BIDSEntities.from_dict(entities).to_path()
    if return_path:
        return name
    elif directory:
        return name.parent
    else:
        return name.name
