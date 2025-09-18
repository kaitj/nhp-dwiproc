"""IO related functions for application."""

import logging
import shutil
from functools import reduce
from pathlib import Path
from typing import Any, Sequence

import polars as pl
from bids2table import load_bids_metadata
from bids2table._pathlib import PathT, as_path
from niwrap_helper import get_bids_table
from niwrap_helper.types import StrPath
from styxdefs import OutputPathType

from ..config.connectivity import ConnectomeConfig, TractMapConfig
from ..config.preprocess import UndistortionConfig
from ..config.shared import GlobalOptsConfig, QueryConfig


def load_participant_table(
    input_dir: StrPath, cfg: GlobalOptsConfig, logger: logging.Logger
) -> pl.DataFrame:
    """Handle loading of bids2table."""
    index_path = cfg.index_path or f"{input_dir}/.index.parquet"
    logger.info(
        "Existing dataset index found"
        if Path(index_path).exists()
        else "Indexing dataset temporarily - run 'index' level analysis instead to save"
    )
    table = get_bids_table(
        dataset_dir=input_dir,
        b2t_index=index_path,
        max_workers=cfg.threads,
        verbose=logger.level < logging.CRITICAL + 1,
    )
    table = pl.from_arrow(table)
    if not isinstance(table, pl.DataFrame):
        raise TypeError(
            f"bids2table output expected to be a DataFrame, got {type(table)}."
        )
    return table


def valid_groupby(df: pl.DataFrame, keys: Sequence[str]) -> list[str]:
    """Return a list of valid keys to group by."""
    return [
        key for key in keys if key in df.columns and df[key].null_count() < df.height
    ]


def query(df: pl.DataFrame, query: str) -> pl.DataFrame:
    """Query data using Polars' SQL syntax.

    NOTE: This function is temporary to provide partial pandas string query support -
    it may be nice to keep this long term, but it largely to replace certain operations.
    """
    query = reduce(
        lambda s, kv: s.replace(*kv), zip(["&", "|", "=="], ["AND", "OR", "="]), query
    )
    return df.sql(f"SELECT * FROM self WHERE {query}")


def get_inputs(
    df: pl.DataFrame,
    row: dict[str, Any],
    query_opts: QueryConfig,
    stage_opts: ConnectomeConfig | TractMapConfig | UndistortionConfig,
    stage: str,
) -> dict[str, Any]:
    """Retrieve relevant inputs for workflow."""

    def _get_file_path(
        entities: dict[str, Any] | None = None,
        queries: list[str] | None = None,
        metadata: bool = False,
    ) -> PathT | dict[str, Any] | None:
        """Retrieve file path from BIDSTable."""
        if entities is not None and queries is not None:
            raise ValueError("Provide only one of 'entities' or 'queries'")

        query_data = pl.DataFrame()
        if queries is not None:
            query_str = " & ".join(queries)
            query_data = query(df=df, query=query_str)
        else:
            all_entities: dict[str, str] = {**row, **(entities or {})}
            # This is to accept a list of possible entities, adapted from b2t v0.1.x
            exprs = [
                (
                    pl.col(k).is_in(v["items"])  # type: ignore[index]
                    if isinstance(v, dict)
                    and "items" in v
                    and isinstance(v["items"], list)
                    else pl.col(k) == v
                )
                for k, v in all_entities.items()
                if k not in {"dataset", "path", "root"} and v is not None
            ]
            expr = reduce(lambda acc, cond: acc & cond, exprs, pl.lit(True))
            query_data = df.filter(expr)

        if query_data.is_empty():
            return None
        else:
            fpath = as_path("/".join(query_data.select(["root", "path"]).row(0)))
            if metadata:
                return load_bids_metadata(fpath)
            return fpath

    def _get_surf_roi_paths(queries: list[str] | None = None) -> list[PathT] | None:
        """Retrieve ROI paths from BIDSTable."""
        if queries is None:
            return None

        surfs_df = query(df, " & ".join(queries))
        return [
            as_path(f"{row['root']}/{row['path']}")
            for row in surfs_df.iter_rows(named=True)
        ]

    sub_ses_query = (
        f"sub = '{row['sub']}'"
        if row["ses"] is None
        else f"sub = '{row['sub']}' AND ses = '{row['ses']}'"
    )
    nii_ext_query = "(ext = '.nii' OR ext = '.nii.gz')"

    # Base inputs
    wf_inputs: dict[str, Any] = {
        "dwi": {
            "nii": _get_file_path(),
            "bval": _get_file_path(entities={"ext": ".bval"}),
            "bvec": _get_file_path(entities={"ext": ".bvec"}),
            "json": _get_file_path(metadata=True) or {},
        },
        "t1w": {
            "nii": _get_file_path(queries=[sub_ses_query, query_opts.t1w])
            if query_opts.t1w is not None
            else _get_file_path(entities={"datatype": "anat", "suffix": "T1w"})
        },
    }

    # Additional inputs to update / grab based on analysis level
    if stage == "preprocess":
        if not isinstance(stage_opts, UndistortionConfig):
            raise TypeError(f"Expected UndistortionConfig, got {type(stage_opts)}")
        if query_opts.mask is not None:
            wf_inputs["dwi"]["mask"] = _get_file_path(
                queries=[sub_ses_query, query_opts.mask]
            )

        match stage_opts.method:
            case "fieldmap":
                fmap_entities = {"datatype": "fmap", "suffix": "epi"}
            case "fugue":
                fmap_entities = {"datatype": "fmap", "suffix": "fieldmap"}
            case _:
                fmap_entities = None  # type: ignore[assignment]
        if fmap_entities is not None:
            fmap_queries = [sub_ses_query, query_opts.fmap or ""]
            wf_inputs["fmap"] = (
                {
                    "nii": _get_file_path(queries=fmap_queries + [nii_ext_query]),
                    "json": _get_file_path(queries=fmap_queries, metadata=True),
                    **(
                        {
                            "bval": _get_file_path(
                                queries=fmap_queries + ["ext=='.bval'"]
                            )
                        }
                        if "epi" in fmap_entities.values()
                        else {}
                    ),
                    **(
                        {
                            "bvec": _get_file_path(
                                queries=fmap_queries + ["ext=='.bvec'"]
                            )
                        }
                        if "epi" in fmap_entities.values()
                        else {}
                    ),
                }
                if query_opts.fmap is not None
                else {
                    "nii": _get_file_path(entities=fmap_entities),
                    "json": _get_file_path(entities=fmap_entities, metadata=True),
                    **(
                        {
                            "bval": _get_file_path(
                                entities={**fmap_entities, "ext": ".bval"}
                            )
                        }
                        if "epi" in fmap_entities.values()
                        else {}
                    ),
                    **(
                        {
                            "bvec": _get_file_path(
                                entities={**fmap_entities, "ext": ".bvec"}
                            )
                        }
                        if "epi" in fmap_entities.values()
                        else {}
                    ),
                }
            )
    else:
        wf_inputs["dwi"]["mask"] = (
            _get_file_path(queries=[sub_ses_query, query_opts.mask])
            if query_opts.mask is not None
            else _get_file_path(entities={"datatype": "anat", "suffix": "mask"})
        )

    if stage == "reconstruction":
        wf_inputs["dwi"]["5tt"] = _get_file_path(
            entities={
                "datatype": "anat",
                "desc": "5tt",
                "suffix": "dseg",
                "ext": {"items": [".nii", ".nii.gz"]},
            }
        )
    elif stage == "connectivity":
        if not isinstance(stage_opts, ConnectomeConfig | TractMapConfig):
            raise TypeError(
                f"Expected ConnectomeConfig or TractMapConfig, got {type(stage_opts)}"
            )
        wf_inputs["dwi"].update(
            {
                "atlas": _get_file_path(
                    entities={
                        "datatype": "anat",
                        "desc": None,
                        "method": None,
                        "seg": stage_opts.atlas,
                        "suffix": "dseg",
                        "ext": {"items": [".nii", ".nii.gz"]},
                    }
                )
                if isinstance(stage_opts, ConnectomeConfig)
                and stage_opts.atlas is not None
                else None,
                "tractography": {
                    key: _get_file_path(
                        entities={
                            "desc": None,
                            "res": None,
                            "method": method,
                            "suffix": suffix,
                            "ext": ext,
                        }
                    )
                    for key, method, suffix, ext in [
                        ("tck_fpath", "iFOD2", "tractography", ".tck"),
                        ("tck_weights_fpath", "SIFT2", "tckWeights", ".txt"),
                    ]
                },
            }
        )

        if (
            isinstance(stage_opts, TractMapConfig)
            and stage_opts.tract_query is not None
        ):
            wf_inputs["anat"] = {
                "rois": {
                    key: _get_surf_roi_paths(
                        queries=[sub_ses_query, stage_opts.tract_query, query]
                    )
                    for key, query in [
                        (
                            "inclusion_fpaths",
                            "desc.str.contains('include|seed|target')",
                        ),
                        ("exclusion_fpaths", "desc.str.contains('exclude')"),
                        ("truncate_fpaths", "desc.str.contains('truncate')"),
                    ]
                },
                "surfs": {
                    surf_type: _get_surf_roi_paths(
                        queries=[
                            sub_ses_query,
                            stage_opts.surface_query,
                            f"suffix=='{surf_type}'",
                        ]
                    )
                    if stage_opts.surface_query is not None
                    else None
                    for surf_type in ["pial", "white", "inflated"]
                },
            }
    return wf_inputs


def save(
    files: OutputPathType | list[OutputPathType],
    out_dir: Path,
) -> None:
    """Save file(s) to specified output directory, preserving directory structure."""

    def _save_file(fpath: Path) -> None:
        """Save individual file, preserving directory structure."""
        for part in fpath.parts:
            if part.startswith("sub-"):
                out_fpath = out_dir / Path(*fpath.parts[fpath.parts.index(part) :])
                out_fpath.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fpath, out_fpath)
                return

        raise ValueError(f"Unable to find relevant file path components for {fpath}")

    # Ensure `files` is iterable and process each one
    for file in [files] if isinstance(files, (str, Path)) else files:
        _save_file(Path(file))


def rename(old_fpath: Path, new_fname: str) -> Path:
    """Rename file."""
    return old_fpath.with_name(new_fname)
