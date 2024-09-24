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
    return (
        index_fpath
        if (index_fpath := cfg.get("opt.index_path"))
        else cfg["bids_dir"] / "index.b2t"
    )


def load_b2t(cfg: dict[str, Any], logger: logging.Logger) -> BIDSTable:
    """Handle loading of bids2table."""
    index_path = check_index_path(cfg=cfg)

    if index_path.exists():
        logger.info("Existing bids2table found")
        if overwrite := cfg["index.overwrite"]:
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
        entities: dict[str, Any] = {},
        queries: list[str] = [],
        metadata: bool = False,
        row: pd.Series = row,
        b2t: BIDSTable = b2t,
    ) -> pl.Path:
        """Internal function to grab file path from b2t."""
        if len(entities) > 0 and (len(queries) > 0):
            raise ValueError("Provide only one of 'entities' or 'query'")
        elif len(queries) > 0:
            query = " & ".join(q for q in queries if q is not None)
            data = b2t.loc[b2t.flat.query(query).index].flat
        else:
            entities_dict = row.dropna().to_dict()
            entities_dict.update(entities)
            data = b2t.filter_multi(**entities_dict).flat

        return data.json.iloc[0] if metadata else pl.Path(data.file_path.iloc[0])

    sub_ses_query = " & ".join(
        [f"{key} == '{value}'" for key, value in row[["sub", "ses"]].to_dict().items()]
    )

    # Base inputs
    wf_inputs = {
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
            wf_inputs["dwi"].update(
                {
                    "mask": _get_file_path(
                        queries=[sub_ses_query, cfg["participant.query_mask"]]
                    )
                }
            )
        if cfg["participant.preprocess.undistort.method"] == "fieldmap":
            if cfg.get("participant.query_fmap") is not None:
                fmap_queries: list[str] = [sub_ses_query, cfg["participant.query_fmap"]]
                wf_inputs.update(
                    {
                        "fmap": {
                            "nii": _get_file_path(
                                queries=(fmap_queries + ["ext=='.nii.gz'"])
                            ),
                            "bval": _get_file_path(
                                queries=(fmap_queries + ["ext=='.bval'"])
                            ),
                            "bvec": _get_file_path(
                                queries=(fmap_queries + ["ext=='.bvec'"])
                            ),
                            "json": _get_file_path(
                                queries=(fmap_queries + ["ext=='.nii.gz'"]),
                                metadata=True,
                            ),
                        }
                    }
                )
            else:
                wf_inputs.update(
                    {
                        "fmap": {
                            "nii": _get_file_path(
                                entities={"datatype": "fmap", "suffix": "epi"}
                            ),
                            "bval": _get_file_path(
                                entities={
                                    "datatype": "fmap",
                                    "suffix": "epi",
                                    "ext": ".bval",
                                }
                            ),
                            "bvec": _get_file_path(
                                entities={
                                    "datatype": "fmap",
                                    "suffix": "epi",
                                    "ext": ".bvec",
                                }
                            ),
                            "json": _get_file_path(
                                entities={
                                    "datatype": "fmap",
                                    "suffix": "epi",
                                    "ext": ".bvec",
                                },
                                metadata=True,
                            ),
                        }
                    }
                )
    else:
        wf_inputs["dwi"].update({"mask": _get_file_path(entities={"suffix": "mask"})})

    if cfg["analysis_level"] == "connectivity":
        wf_inputs.update(
            {
                "atlas": {
                    "nii": _get_file_path(
                        entities={
                            "space": "T1w",
                            "seg": cfg.get("participant.connectivity.atlas"),
                            "suffix": "dseg",
                        }
                    )
                },
                "tractography": {
                    "tck": _get_file_path(
                        entities={
                            "method": "iFOD2",
                            "suffix": "tractography",
                            "ext": ".tck",
                        }
                    ),
                    "weights": _get_file_path(
                        entities={
                            "method": "SIFT2",
                            "suffix": "tckWeights",
                            "ext": ".txt",
                        }
                    ),
                },
            }
        )

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
