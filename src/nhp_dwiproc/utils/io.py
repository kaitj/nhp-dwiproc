"""IO related functions for application."""

import shutil
from logging import Logger
from pathlib import Path
from typing import Any, Literal, overload

import pandas as pd
from bids2table import BIDSEntities, BIDSTable, bids2table
from styxdefs import OutputPathType


def check_index_path(cfg: dict[str, Any]) -> Path:
    """Check for index path."""
    return cfg.get("opt.index_path", cfg["bids_dir"] / "index.b2t")


def load_b2t(cfg: dict[str, Any], logger: Logger) -> pd.DataFrame:
    """Handle loading of bids2table."""
    index_path = check_index_path(cfg=cfg)
    overwrite = cfg.get("index.overwrite", False) if index_path.exists() else False

    logger.info(
        "Existing bids2table found" if index_path.exists() else "Indexing BIDS dataset"
    )
    if overwrite:
        logger.info("Overwriting existing table")
    elif not index_path.exists():
        logger.warning(
            "Index created but not saved - run 'index' level analysis to save"
        )

    b2t = bids2table(
        root=cfg["bids_dir"],
        index_path=index_path if index_path.exists() else None,
        workers=cfg.get("opt.threads", 1),
        overwrite=overwrite,
    )

    # Extract and flatten extra entities
    extra_entities = pd.json_normalize(b2t.pop("ent__extra_entities")).set_index(  # type: ignore
        b2t.index  # type: ignore
    )
    return pd.concat([b2t, extra_entities.add_prefix("ent__")], axis=1)


def valid_groupby(b2t: BIDSTable, keys: list[str]) -> list[str]:
    """Return a list of valid keys to group by."""
    return [f"ent__{key}" for key in keys if b2t[f"ent__{key}"].notna().any()]


def get_inputs(
    b2t: BIDSTable,
    row: pd.Series,
    cfg: dict[str, Any],
) -> dict[str, Any]:
    """Retrieve relevant inputs for workflow."""

    def _get_file_path(
        entities: dict[str, Any] | None = None,
        queries: list[str] | None = None,
        metadata: bool = False,
    ) -> Path | None:
        """Retrieve file path from BIDSTable."""
        if entities and queries:
            raise ValueError("Proivde only one of 'entities' or 'queries'")

        query_data = (
            b2t.loc[b2t.flat.query(" & ".join(queries)).index].flat
            if queries
            else b2t.filter_multi(
                **{
                    k: v
                    for k, v in {**row.dropna().to_dict(), **(entities or {})}.items()
                    if v is not None
                }
            ).flat
        )

        return (
            None
            if query_data.empty
            else (
                query_data.json.iloc[0]
                if metadata
                else Path(query_data.file_path.iloc[0])
            )
        )

    def _get_surf_roi_paths(queries: list[str] | None = None) -> list[Path] | None:
        """Retrieve ROI paths from BIDSTable."""
        return (
            list(map(Path, b2t.flat.query(" & ".join(queries)).file_path))
            if queries
            else None
        )

    sub_ses_query = " & ".join(
        f"{k} == '{v}'" for k, v in row[["sub", "ses"]].to_dict().items()
    )
    nii_ext_query = "(ext == '.nii' or ext == '.nii.gz')"

    # Base inputs
    wf_inputs: dict[str, Any] = {
        "dwi": {
            "nii": _get_file_path(),
            "bval": _get_file_path(entities={"ext": ".bval"}),
            "bvec": _get_file_path(entities={"ext": ".bvec"}),
            "json": _get_file_path(metadata=True),
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
                        ("tck", "iFOD2", "tractography", ".tck"),
                        ("weights", "SIFT2", "tckWeights", ".txt"),
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
                        ("inclusion", "desc.str.contains('include|seed|target')"),
                        ("exclusion", "desc.str.contains('exclude')"),
                        ("stop", "desc.str.contains('truncate')"),
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
                out_fpath = out_dir.joinpath(*fpath.parts[fpath.parts.index(part) :])
                out_fpath.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(fpath, out_fpath)
                return

        raise ValueError(f"Unable to find relevant file path components for {fpath}")

    # Ensure `files` is iterable and process each one
    for file in [files] if isinstance(files, (str, Path)) else files:
        _save_file(Path(file))


@overload
def bids_name(
    directory: Literal[False], return_path: Literal[False], **entities
) -> str: ...


@overload
def bids_name(
    directory: Literal[False], return_path: Literal[True], **entities
) -> Path: ...


@overload
def bids_name(
    directory: Literal[True], return_path: Literal[False], **entities
) -> Path: ...


def bids_name(
    directory: bool = False, return_path: bool = False, **entities
) -> Path | str:
    """Helper function to generate bids-esque name."""
    if directory and return_path:
        raise ValueError("Only one of 'directory' or 'return_path' can be True")

    name = BIDSEntities.from_dict(entities).to_path()
    return name if return_path else name.parent if directory else name.name


def rename(old_fpath: Path, new_fname: str) -> Path:
    """Rename file."""
    return old_fpath.with_name(new_fname)
