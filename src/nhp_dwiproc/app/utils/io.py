"""IO related functions for application."""

import logging
import pathlib as pl
import shutil
from typing import Any

import pandas as pd
from bids2table import BIDSTable, bids2table
from styxdefs import OutputPathType


def check_index_path(cfg: dict[str, Any]) -> pl.Path:
    """Helper to check for index path."""
    return cfg.get("opt.index_path", cfg["bids_dir"] / "index.b2t")


def load_b2t(cfg: dict[str, Any], logger: logging.Logger) -> BIDSTable:
    """Handle loading of bids2table."""
    index_path = check_index_path(cfg=cfg)

    if index_path.exists():
        logger.info("Existing bids2table found")
        overwrite = cfg.get("index.overwrite", False)
        if overwrite:
            logger.info("Overwriting existing table")
    else:
        logger.info("Indexing bids dataset")
        overwrite = False
        logger.warning(
            "Index created, but not saved - please run 'index' level analysis to save"
        )

    b2t = bids2table(
        root=cfg["bids_dir"],
        index_path=index_path if index_path.exists() else None,
        workers=cfg.get("opt.threads", 1),
        overwrite=overwrite,
    )

    # Flatten entities s.t. extra_ents can be filtered
    extra_entities = pd.json_normalize(b2t["ent__extra_entities"]).set_index(b2t.index)
    b2t = pd.concat([b2t, extra_entities.add_prefix("ent__")], axis=1)

    return b2t.drop(columns="ent__extra_entities")


def valid_groupby(b2t: BIDSTable, keys: list[str]) -> list[str]:
    """Return a list of valid keys to group by."""
    return [f"ent__{key}" for key in keys if b2t[f"ent__{key}"].notna().any()]


def get_inputs(
    b2t: BIDSTable,
    row: pd.Series,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Helper to grab relevant inputs for workflow."""

    def _get_file_path(
        entities: dict[str, Any] | None = None,
        queries: list[str] | None = None,
        metadata: bool = False,
        row: pd.Series = row,
        b2t: BIDSTable = b2t,
    ) -> pl.Path | None:
        """Internal function to grab file path from b2t."""
        if entities and queries:
            raise ValueError("Proivde only one of 'entities' or 'queries'")

        if queries:
            query = " & ".join(queries)
            data = b2t.loc[b2t.flat.query(query).index].flat
        else:
            entities_dict = row.dropna().to_dict()
            entities_dict.update(entities or {})
            data = b2t.filter_multi(
                **{k: v for k, v in entities_dict.items() if v is not None}
            ).flat

        if data.empty:
            return None
        return data.json.iloc[0] if metadata else pl.Path(data.file_path.iloc[0])

    def _get_surf_roi_paths(
        queries: list[str] | None = None,
        b2t: BIDSTable = b2t,
    ) -> list[pl.Path] | None:
        """Internal function to help grab ROI paths."""
        if not queries or len(queries) == 0:
            return None
        query = " & ".join(queries)
        return list(map(pl.Path, b2t.flat.query(query).file_path))

    sub_ses_query = " & ".join(
        [f"{key} == '{value}'" for key, value in row[["sub", "ses"]].to_dict().items()]
    )
    nii_ext_query = "ext=='.nii' or ext=='.nii.gz'"

    # Base inputs
    wf_inputs: dict[str, Any] = {
        "dwi": {
            "nii": _get_file_path(),
            "bval": _get_file_path(entities={"ext": ".bval"}),
            "bvec": _get_file_path(entities={"ext": ".bvec"}),
            "json": _get_file_path(metadata=True),
        },
        "t1w": {
            "nii": (
                _get_file_path(queries=[sub_ses_query, cfg["participant.query_t1w"]])
                if cfg.get("participant.query_t1w")
                else _get_file_path(entities={"datatype": "anat", "suffix": "T1w"})
            )
        },
    }

    # Additional inputs to update / grab based on analysis level
    if cfg["analysis_level"] == "preprocess":
        if cfg.get("participant.query_mask"):
            wf_inputs["dwi"]["mask"] = _get_file_path(
                queries=[sub_ses_query, cfg["participant.query_mask"]]
            )

        if cfg["participant.preprocess.undistort.method"] == "fieldmap":
            fmap_queries: list[str] = [sub_ses_query, cfg["participant.query_fmap"]]
            fmap_entities = {"datatype": "fmap", "suffix": "epi"}
            wf_inputs["fmap"] = (
                {
                    "nii": _get_file_path(queries=fmap_queries + [nii_ext_query]),
                    "bval": _get_file_path(queries=fmap_queries + ["ext=='.bval'"]),
                    "bvec": _get_file_path(queries=fmap_queries + ["ext=='.bvec'"]),
                    "json": _get_file_path(queries=fmap_queries + [], metadata=True),
                }
                if cfg.get("participant.query_fmap")
                else {
                    "nii": _get_file_path(entities=fmap_entities),
                    "bval": _get_file_path(entities={**fmap_entities, "ext": ".bval"}),
                    "bvec": _get_file_path(entities={**fmap_entities, "ext": ".bvec"}),
                    "json": _get_file_path(entities=fmap_entities, metadata=True),
                }
            )
    else:
        wf_inputs["dwi"]["mask"] = (
            _get_file_path(queries=[sub_ses_query, cfg["participant.query_mask"]])
            if cfg.get("participant.query_mask")
            else _get_file_path(entities={"datatype": "anat", "suffix": "mask"})
        )

    # Expect single 5tt image
    if cfg["analysis_level"] == "tractography":
        wf_inputs["dwi"]["5tt"] = _get_file_path(
            entities={
                "datatype": "anat",
                "desc": "5tt",
                "suffix": "dseg",
                "ext": {"items": [".nii", ".nii.gz"]},
            }
        )

    # Set desc to 'None' to reset entity search
    elif cfg["analysis_level"] == "connectivity":
        wf_inputs["dwi"].update(
            {
                "atlas": _get_file_path(
                    entities={
                        "datatype": "anat",
                        "desc": None,
                        "method": None,
                        "seg": cfg.get("participant.connectivity.atlas", ""),
                        "suffix": "dseg",
                        "ext": {"items": [".nii", ".nii.gz"]},
                    }
                )
                if cfg.get("participant.connectivity.atlas")
                else None,
                "tractography": {
                    "tck": _get_file_path(
                        entities={
                            "desc": None,
                            "res": None,
                            "method": "iFOD2",
                            "suffix": "tractography",
                            "ext": ".tck",
                        }
                    ),
                    "weights": _get_file_path(
                        entities={
                            "desc": None,
                            "res": None,
                            "method": "SIFT2",
                            "suffix": "tckWeights",
                            "ext": ".txt",
                        }
                    ),
                },
            }
        )
        if not cfg.get("participant.connectivity.atlas", None) and (
            tract_query := cfg.get("participant.connectivity.query_tract")
        ):
            wf_inputs["anat"] = {
                "rois": {
                    "inclusion": _get_surf_roi_paths(
                        queries=[
                            sub_ses_query,
                            tract_query,
                            "desc.str.contains('include|seed|target')",
                        ]
                    ),
                    "exclusion": _get_surf_roi_paths(
                        queries=[
                            sub_ses_query,
                            tract_query,
                            "desc.str.contains('exclude')",
                        ]
                    ),
                    "stop": _get_surf_roi_paths(
                        queries=[
                            sub_ses_query,
                            tract_query,
                            "desc.str.contains('truncate')",
                        ]
                    ),
                },
                "surfs": {
                    surf_type: _get_surf_roi_paths(
                        queries=[
                            sub_ses_query,
                            cfg.get("participant.connectivity.query_surf", None),
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
    out_dir: pl.Path,
) -> None:
    """Helper function to save file(s) to disk."""

    def _save_file(fpath: pl.Path) -> None:
        """Internal function to save file."""
        try:
            sub_idx = next(
                idx for idx, part in enumerate(fpath.parts) if "sub-" in part
            )
        except StopIteration:
            raise ValueError(
                f"Unable to find relevant file path components for {fpath}"
            )

        out_fpath = out_dir.joinpath(*fpath.parts[sub_idx:])
        out_fpath.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(fpath, out_fpath)

    # Recursively call save for each file in list
    if isinstance(files, list):
        for file in files:
            _save_file(pl.Path(file))
    else:
        _save_file(pl.Path(files))


def rename(old_fpath: pl.Path, new_fname: str) -> pl.Path:
    """Helper function to rename files."""
    return old_fpath.with_name(new_fname)
