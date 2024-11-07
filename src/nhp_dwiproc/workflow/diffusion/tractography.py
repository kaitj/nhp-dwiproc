"""Tractography-related operations."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix
from styxdefs import InputPathType

from nhp_dwiproc.app import utils


def _tckgen(
    wm_fod: InputPathType,
    tt_map: InputPathType,
    bids: partial[str],
    cfg: dict[str, Any],
    **kwargs,
) -> mrtrix.TckgenOutputs:
    """Generate tractography with selected method."""
    # Common parameters
    tckgen_params = {
        "source": wm_fod,
        "tracks": bids(method="iFOD2", suffix="tractography", ext=".tck"),
        "algorithm": "iFOD2",
        "seed_dynamic": wm_fod,
        "step": cfg.get("participant.tractography.steps"),
        "cutoff": cfg.get("participant.tractography.cutoff"),
        "select_": cfg.get("participant.tractography.streamlines"),
        "nthreads": cfg.get("opt.threads"),
    }

    # ACT-specific params
    if cfg["participant.tractography.method"] == "act":
        tckgen_params.update(
            {
                "act": tt_map,
                "backtrack": cfg["participant.tractography.act.backtrack"],
                "crop_at_gmwmi": not cfg["participant.tractography.act.nocrop_gmwmi"],
            }
        )

    return mrtrix.tckgen(**tckgen_params)


def generate_tractography(
    input_data: dict[str, Any],
    input_group: dict[str, Any],
    fod: mrtrix.MtnormaliseOutputs,
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> None:
    """Generate subject tractography."""
    logger.info("Generating tractography")
    wm_fod = fod.input_output[0].output
    bids = partial(
        utils.bids_name,
        datatype="dwi",
        **input_group,
    )
    tckgen = _tckgen(
        wm_fod=wm_fod,
        tt_map=input_data["dwi"].get("5tt", None),
        bids=bids,
        cfg=cfg,
    )

    logger.info("Computing per-streamline multipliers")
    tcksift = mrtrix.tcksift2(
        in_tracks=tckgen.tracks,
        in_fod=wm_fod,
        out_weights=bids(
            method="SIFT2",
            suffix="tckWeights",
            ext=".txt",
        ),
        nthreads=cfg["opt.threads"],
    )

    tdi = {}
    for meas, weights in zip(["raw", "weighted"], [None, tcksift.out_weights]):
        tdi[meas] = mrtrix.tckmap(
            tracks=tckgen.tracks,
            tck_weights_in=weights,
            template=wm_fod,
            output=bids(
                meas=meas,
                suffix="tdi",
                ext=".nii.gz",
            ),
            nthreads=cfg["opt.threads"],
        )

    # Save relevant outputs
    utils.io.save(
        files=[tckgen.tracks, tcksift.out_weights, tdi["weighted"].output],
        out_dir=cfg["output_dir"].joinpath(bids(directory=True)),
    )
