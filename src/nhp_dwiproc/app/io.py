"""IO related functions for application."""

import logging
from functools import reduce
from pathlib import Path
from typing import Any, Sequence

import polars as pl
from bids2table import load_bids_metadata
from niwrap_helper import get_bids_table
from niwrap_helper.bids import PathT, StrPath, as_path

from .. import config as cfg_


def load_participant_table(
    input_dir: StrPath,
    cfg: cfg_.GlobalOptsConfig,
    logger: logging.Logger = logging.Logger(__name__),
) -> pl.DataFrame:
    """Handle loading of bids2table.

    Args:
        input_dir: Path to input dataset directory.
        cfg: Global configuration options.
        logger: Logging object.


    Returns:
        bids2table dataframe associated with dataset indexed.

    Raises:
        TypeError: if output is not a DataFrame object.
    """
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
    return table


def valid_groupby(df: pl.DataFrame, keys: Sequence[str]) -> list[str]:
    """Return a list of valid keys to group by.

    Args:
        df: DataFrame to identify valid keys.
        keys: List of values to group bids2table by.

    Returns:
        List of valid keys found in the DataFrame with entities.
    """
    return [
        key for key in keys if key in df.columns and df[key].null_count() < df.height
    ]


def query(df: pl.DataFrame, query: str) -> pl.DataFrame:
    """Query data using Polars' SQL syntax.

    Args:
        df: DataFrame to query.
        query: Query string to update and query by.

    Returns:
        Dataframe containing only rows with matching entities from the query.

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
    query_opts: cfg_.QueryConfig,
    stage_opts: cfg_.connectivity.ConnectomeConfig
    | cfg_.connectivity.TractMapConfig
    | cfg_.preprocess.UndistortionConfig
    | None,
    stage: str,
) -> dict[str, Any]:
    """Retrieve relevant inputs for workflow.

    Args:
        df: Dataset dataframe to query inputs from.
        row: Dictionary containing relevant BIDS entities for further filtering.
        query_opts: Query arguments passed for filtering.
        stage_opts: Stage-specific configuration options.
        stage: Processing stage.

    Returns:
        Dictionary containing filepaths required to process desired stage.

    Raises:
        TypeError: If expected configuration option of the incorrect type.
    """

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
                if k in df.columns
                and k not in {"dataset", "path", "root"}
                and v is not None
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
        if not isinstance(stage_opts, cfg_.preprocess.UndistortionConfig):
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
        if not isinstance(
            stage_opts,
            cfg_.connectivity.ConnectomeConfig | cfg_.connectivity.TractMapConfig,
        ):
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
                if isinstance(stage_opts, cfg_.connectivity.ConnectomeConfig)
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
            isinstance(stage_opts, cfg_.connectivity.TractMapConfig)
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
                            """desc LIKE '%include%' OR desc LIKE '%seed%' OR
                            desc LIKE '%target%'""",
                        ),
                        ("exclusion_fpaths", "desc LIKE '%exclude%'"),
                        ("truncate_fpaths", "desc LIKE '%truncate%'"),
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
