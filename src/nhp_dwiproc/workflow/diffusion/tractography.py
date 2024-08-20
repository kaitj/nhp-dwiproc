"""Tractography generation."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix

from nhp_dwiproc.app import utils


def generate_tractography(
    input_data: dict[str, Any],
    fod: mrtrix.MtnormaliseOutputs,
    cfg: dict[str, Any],
    logger: Logger,
) -> None:
    """Generate subject tractography."""
    logger.info("Generating tractography")
    wm_fod = fod.input_output[0].output
    bids = partial(
        utils.bids_name,
        datatype="dwi",
        **input_data["entities"],
    )

    tckgen = mrtrix.tckgen(
        source=wm_fod,
        tracks=bids(
            method="iFOD2",
            suffix="tractography",
            ext=".tck",
        ),
        mask=[mrtrix.TckgenMask(input_data["dwi"]["mask"])],
        seed_dynamic=wm_fod,
        algorithm="iFOD2",
        step=steps if (steps := cfg["participant.tractography.steps"]) else None,
        cutoff=cfg["participant.tractography.cutoff"],
        select_=cfg["participant.tractography.streamlines"],
        nthreads=cfg["opt.threads"],
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
    utils.save(
        files=[tckgen.tracks, tcksift.out_weights, tdi["weighted"].output],
        out_dir=cfg["output_dir"].joinpath(bids(directory=True)),
    )
