"""Pre-tractography participant processing (to compute FODs)."""

from functools import partial
from logging import Logger
from typing import Any

import niwrap_helper
from bids2table import BIDSTable
from tqdm import tqdm

from nhp_dwiproc import utils
from nhp_dwiproc.workflow.diffusion import connectivity


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for connectivity analysis-level."""
    logger.info("Connectivity analysis-level")
    if cfg.get("participant.connectivity.atlas") and (
        cfg.get("participant.connectivity.query_surf")
        or cfg.get("participant.connectivity.query_include")
        or cfg.get("participant.connectivity.query_exclude")
        or cfg.get("participant.connectivity.query_truncate")
    ):
        raise ValueError("Only one of atlas or ROIs should be provided")

    # Load BIDSTable, querying if necessary
    b2t = utils.io.load_b2t(cfg=cfg, logger=logger)
    if cfg.get("participant.query"):
        b2t = b2t.loc[b2t.flat.query(cfg.get("participant.query", "")).index]
    if not isinstance(b2t, BIDSTable):
        raise TypeError(f"Loaded table of type {type(b2t)} instead of BIDSTable")

    # Loop through remaining subjects after query
    dwi_b2t = b2t
    if cfg.get("participant.query_dwi"):
        dwi_b2t = b2t.loc[b2t.flat.query(cfg["participant.query_dwi"]).index]
    if not isinstance(dwi_b2t, BIDSTable):
        raise TypeError(f"Queried table of type {type(dwi_b2t)} instead of BIDSTable")

    groupby_keys = utils.io.valid_groupby(
        b2t=dwi_b2t, keys=["sub", "ses", "run", "space"]
    )
    for group_vals, group in tqdm(
        dwi_b2t.filter_multi(suffix="tractography", ext=".tck").groupby(groupby_keys)
    ):
        for _, row in group.ent.iterrows():
            input_data = utils.io.get_inputs(b2t=b2t, row=row, cfg=cfg)
            input_group = dict(
                zip([key.lstrip("ent__") for key in groupby_keys], group_vals)
            )

            # Perform processing
            uid = niwrap_helper.bids_path(**input_group)
            logger.info(f"Processing {uid}")
            bids = partial(niwrap_helper.bids_path, datatype="dwi", **input_group)
            output_fpath = cfg["output_dir"] / bids(directory=True)

            # Generate connectivity matrices
            if cfg.get("participant.connectivity.atlas"):
                logger.info("Generating connectivity matrices")
                connectivity.generate_conn_matrix(
                    atlas_fpath=input_data["dwi"]["atlas"],
                    **input_data["dwi"]["tractography"],
                    search_radius=cfg["participant.connectivity.radius"],
                    output_fpath=output_fpath,
                    bids=bids,
                )

            # Perform tract extraction and optional surface mapping
            elif cfg.get("participant.connectivity.query_tract"):
                logger.info("Extracting tract")
                tdi, hemi, label = connectivity.extract_tract(
                    **input_data["dwi"]["tractography"],
                    **input_data["anat"]["rois"],
                    voxel_size=[vox]
                    if (vox := cfg.get("participant.connectivity.vox_mm"))
                    else None,
                    output_fpath=output_fpath,
                    bids=bids,
                )

                if not input_data["anat"]["surfs"].get("inflated"):
                    logger.warning("Inflated surface not found; not mapping end points")
                else:
                    for surf_type in ["white", "pial", "inflated"]:
                        if len(surfs := input_data["anat"]["surfs"][surf_type]) > 1:
                            logger.warning(
                                f"More than 1 surface found: {surfs} - using "
                                "first surface"
                            )
                    logger.info("Mapping tract to surface")
                    connectivity.surface_map_tract(
                        tdi=tdi,
                        hemi=hemi,
                        label=label,
                        **input_data["anat"]["surfs"],
                        output_fpath=output_fpath,
                        bids=bids,
                    )
            else:
                raise ValueError("No valid inputs provided for connectivity workflow")
            logger.info(f"Completed processing for {uid}")
