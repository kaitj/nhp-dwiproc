"""Generation of connectivity files."""

from functools import partial
from logging import Logger
from typing import Any

from bids2table import BIDSEntities
from niwrap import mrtrix, workbench

import nhp_dwiproc.utils as utils


def generate_conn_matrix(
    input_data: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> None:
    """Generate connectivity matrix."""
    logger.info("Generating connectivity matrices")
    bids = partial(utils.io.bids_name, datatype="dwi", **input_group)
    tck2connectome = {}
    for meas, tck_weights, length in zip(
        ["afd", "count", "avgLength"],
        [input_data["dwi"]["tractography"]["weights"], None, None],
        [False, False, True],
    ):
        tck2connectome[meas] = mrtrix.tck2connectome(
            tracks_in=input_data["dwi"]["tractography"]["tck"],
            nodes_in=input_data["dwi"]["atlas"],
            connectome_out=bids(
                meas=meas, desc="probabilisticTracking", suffix="relmap", ext=".csv"
            ),
            assignment_radial_search=cfg["participant.connectivity.radius"],
            out_assignments=bids(desc="assignment", suffix="tractography", ext=".txt"),
            tck_weights_in=tck_weights,
            scale_length=length,
            stat_edge="mean" if length else None,
        )

        # Save outputs
        utils.io.save(
            files=tck2connectome[meas].connectome_out,
            out_dir=cfg["output_dir"] / bids(directory=True),
        )


def extract_tract(
    input_data: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> None:
    """Extract individual tract."""
    # Organize ROIs and get tract label
    incl_rois = [
        mrtrix.tckedit_include_params(spec=mrtrix.tckedit_various_file_params(fpath))
        for fpath in input_data["anat"]["rois"]["inclusion"]
    ]
    excl_rois = [
        mrtrix.tckedit_exclude_params(spec=mrtrix.tckedit_various_file_1_params(fpath))
        for fpath in input_data["anat"]["rois"]["exclusion"]
    ]
    truncate_rois = [
        mrtrix.tckedit_mask_params(spec=mrtrix.tckedit_various_file_2_params(fpath))
        for fpath in input_data["anat"]["rois"]["stop"]
    ]
    rois = [*incl_rois, *excl_rois, *truncate_rois]
    if len(rois) == 0:
        raise ValueError("No ROIs were provided")

    logger.info("Extracting tract")
    bids = partial(utils.io.bids_name, datatype="dwi", **input_group)

    tract_entities = BIDSEntities.from_path(rois[0].spec.obj)
    label = tract_entities.label
    hemi = tract_entities.hemi
    tckedit = mrtrix.tckedit(
        tracks_in=[input_data["dwi"]["tractography"]["tck"]],
        tracks_out=bids(
            hemi=hemi, label=label, method="iFOD2", suffix="tractograhy", ext=".tck"
        ),
        include=incl_rois,
        exclude=excl_rois,
        mask=truncate_rois,
        tck_weights_in=input_data["dwi"]["tractography"]["weights"],
        tck_weights_out=bids(
            hemi=hemi, label=label, method="SIFT2", suffix="tckWeights", ext=".txt"
        ),
    )
    tdi = mrtrix.tckmap(
        tracks=tckedit.tracks_out,
        tck_weights_in=tckedit.tck_weights_out,
        vox=[vox] if (vox := cfg.get("participant.connectivity.vox_mm")) else None,
        template=rois[0].spec.obj,
        output=bids(hemi=hemi, label=label, suffix="tdi", ext=".nii.gz"),
    )

    utils.io.save(files=tdi.output, out_dir=cfg["output_dir"] / bids(directory=True))

    # Map to surface
    if not input_data["anat"]["surfs"].get("inflated"):
        logger.warning("Inflated surface not found; not mapping end points")
    else:
        for surf_type in ["white", "pial", "inflated"]:
            if len(input_data["anat"]["surfs"][surf_type]) > 1:
                raise ValueError(f"More than 1 surface found for {surf_type}")
        surf = workbench.volume_to_surface_mapping(
            volume=tdi.output,
            surface=input_data["anat"]["surfs"]["inflated"][0],
            metric_out=bids(hemi=hemi, label=label, suffix="conn", ext=".shape.gii"),
            ribbon_constrained=(
                workbench.volume_to_surface_mapping_ribbon_constrained_params(
                    inner_surf=input_data["anat"]["surfs"]["white"][0],
                    outer_surf=input_data["anat"]["surfs"]["pial"][0],
                )
            ),
        )

        utils.io.save(
            files=surf.metric_out, out_dir=cfg["output_dir"] / bids(directory=True)
        )
