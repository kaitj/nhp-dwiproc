"""IO related functions for application."""

import shutil
from functools import reduce
from logging import Logger
from pathlib import Path
from typing import Any, Sequence

import polars as pl
from bids2table import load_bids_metadata
from bids2table._pathlib import PathT, as_path
from niwrap_helper.bids import get_bids_table
from styxdefs import OutputPathType


def load_participant_table(cfg: dict[str, Any], logger: Logger) -> pl.DataFrame:
    """Handle loading of bids2table."""
    index_path = as_path(cfg.get("opt.index_path", cfg["bids_dir"] / ".index.parquet"))
    index_exists = index_path.exists()

    if index_exists:
        logger.info("Existing dataset index found")
    else:
        logger.info("Indexing dataset - run 'index' level analysis instead to save")

    table = get_bids_table(dataset_dir=cfg["bids_dir"], index=index_path)
    return pl.from_arrow(table)


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
    cfg: dict[str, Any],
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
            "nii": _get_file_path(queries=[sub_ses_query, cfg["participant.query_t1w"]])
            if cfg.get("participant.query_t1w")
            else _get_file_path(entities={"datatype": "anat", "suffix": "T1w"})
        },
    }

    # Additional inputs to update / grab based on analysis level
    if cfg["analysis_level"] == "preprocess":
        if mask_query := cfg.get("participant.query_mask"):
            wf_inputs["dwi"]["mask"] = _get_file_path(
                queries=[sub_ses_query, mask_query]
            )

        match cfg["participant.preprocess.undistort.method"]:
            case "fieldmap":
                fmap_entities = {"datatype": "fmap", "suffix": "epi"}
            case "fugue":
                fmap_entities = {"datatype": "fmap", "suffix": "fieldmap"}
            case _:
                fmap_entities = None  # type: ignore[assignment]
        if fmap_entities:
            fmap_queries = [sub_ses_query, cfg.get("participant.query_fmap", "")]
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
                if cfg.get("participant.query_fmap")
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
            _get_file_path(queries=[sub_ses_query, cfg["participant.query_mask"]])
            if cfg.get("participant.query_mask")
            else _get_file_path(entities={"datatype": "anat", "suffix": "mask"})
        )

    if cfg["analysis_level"] == "tractography":
        wf_inputs["dwi"]["5tt"] = _get_file_path(
            entities={
                "datatype": "anat",
                "desc": "5tt",
                "suffix": "dseg",
                "ext": {"items": [".nii", ".nii.gz"]},
            }
        )

    elif cfg["analysis_level"] == "connectivity":
        atlas_query = cfg.get("participant.connectivity.atlas", "")
        wf_inputs["dwi"].update(
            {
                "atlas": _get_file_path(
                    entities={
                        "datatype": "anat",
                        "desc": None,
                        "method": None,
                        "seg": atlas_query,
                        "suffix": "dseg",
                        "ext": {"items": [".nii", ".nii.gz"]},
                    }
                )
                if atlas_query
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

        if not atlas_query and (
            tract_query := cfg.get("participant.connectivity.query_tract")
        ):
            wf_inputs["anat"] = {
                "rois": {
                    key: _get_surf_roi_paths(
                        queries=[sub_ses_query, tract_query, query]
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
                            cfg.get("participant.connectivity.query_surf", ""),
                            f"suffix=='{surf_type}'",
                        ]
                    )
                    if cfg.get("participant.connectivity.query_surf")
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
