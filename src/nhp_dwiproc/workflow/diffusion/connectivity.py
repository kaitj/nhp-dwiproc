"""Generation of connectivity files."""

from functools import partial
from pathlib import Path

import niwrap_helper
from bids2table import BIDSEntities
from niwrap import mrtrix, workbench

import nhp_dwiproc.utils as utils


def generate_conn_matrix(
    atlas_fpath: Path,
    tck_fpath: Path,
    tck_weights_fpath: Path | None,
    search_radius: float,
    output_fpath: Path = Path.cwd(),
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
) -> None:
    """Generate connectivity matrix."""
    tck2connectome = {}
    for meas, tck_weights, length in zip(
        ["afd", "count", "avgLength"],
        [tck_weights_fpath, None, None],
        [False, False, True],
    ):
        tck2connectome[meas] = mrtrix.tck2connectome(
            tracks_in=tck_fpath,
            nodes_in=atlas_fpath,
            connectome_out=bids(
                meas=meas, desc="probabilisticTracking", suffix="relmap", ext=".csv"
            ),
            assignment_radial_search=search_radius,
            out_assignments=bids(desc="assignment", suffix="tractography", ext=".txt"),
            tck_weights_in=tck_weights,
            scale_length=length,
            stat_edge="mean" if length else None,
        )
        utils.io.save(files=tck2connectome[meas].connectome_out, out_dir=output_fpath)


def extract_tract(
    tck_fpath: Path,
    tck_weights_fpath: Path | None,
    include_fpaths: list[Path],
    exclude_fpaths: list[Path],
    truncate_fpaths: list[Path],
    voxel_size: list[float] | None,
    output_fpath: Path = Path.cwd(),
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
) -> tuple[mrtrix.TckmapOutputs, str | None, str | None]:
    """Extract individual tract."""
    # Organize ROIs and get tract label
    if voxel_size and (len(voxel_size) > 3 or len(voxel_size) != 1):
        raise ValueError("Unexpected number of voxels provided.")

    incl_rois = [
        mrtrix.tckedit_include_params(spec=mrtrix.tckedit_various_file_params(fpath))
        for fpath in include_fpaths
    ]
    excl_rois = [
        mrtrix.tckedit_exclude_params(spec=mrtrix.tckedit_various_file_1_params(fpath))
        for fpath in exclude_fpaths
    ]
    truncate_rois = [
        mrtrix.tckedit_mask_params(spec=mrtrix.tckedit_various_file_2_params(fpath))
        for fpath in truncate_fpaths
    ]
    rois = [*incl_rois, *excl_rois, *truncate_rois]
    if len(rois) == 0:
        raise ValueError("No ROIs were provided")

    tract_entities = BIDSEntities.from_path(rois[0].spec.obj)
    label = tract_entities.label
    hemi = tract_entities.hemi
    tckedit = mrtrix.tckedit(
        tracks_in=[tck_fpath],
        tracks_out=bids(
            hemi=hemi, label=label, method="iFOD2", suffix="tractograhy", ext=".tck"
        ),
        include=incl_rois,
        exclude=excl_rois,
        mask=truncate_rois,
        tck_weights_in=tck_weights_fpath,
        tck_weights_out=bids(
            hemi=hemi, label=label, method="SIFT2", suffix="tckWeights", ext=".txt"
        ),
    )
    tdi = mrtrix.tckmap(
        tracks=tckedit.tracks_out,
        tck_weights_in=tckedit.tck_weights_out,
        vox=voxel_size,
        template=rois[0].spec.obj,
        output=bids(hemi=hemi, label=label, suffix="tdi", ext=".nii.gz"),
    )
    utils.io.save(files=tdi.output, out_dir=output_fpath)

    return tdi, hemi, label


def surface_map_tract(
    tdi: mrtrix.TckmapOutputs,
    hemi: str | None,
    label: str | None,
    white: list[Path],
    pial: list[Path],
    inflated: list[Path],
    output_fpath: Path = Path.cwd(),
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
) -> None:
    """Surface map extracted tract."""
    surf = workbench.volume_to_surface_mapping(
        volume=tdi.output,
        surface=inflated[0],
        metric_out=bids(hemi=hemi, label=label, suffix="conn", ext=".shape.gii"),
        ribbon_constrained=(
            workbench.volume_to_surface_mapping_ribbon_constrained_params(
                inner_surf=white[0],
                outer_surf=pial[0],
            )
        ),
    )
    utils.io.save(files=surf.metric_out, out_dir=output_fpath)
