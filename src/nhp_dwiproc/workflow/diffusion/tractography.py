"""Tractography generation."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix

from ...app import utils


def generate_tractography(
    input_data: dict[str, Any],
    fod: mrtrix.MtnormaliseOutputs,
    bids: partial,
    cfg: dict[str, Any],
    logger: Logger,
) -> None:
    """Generate subject tractography."""
    logger.info("Generating tractography")
    wm_fod = fod.input_output[0].output

    tckgen = mrtrix.tckgen(
        source=wm_fod,
        tracks=bids(desc="iFOD2", suffix="tractography", ext=".tck").to_path().name,
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
        out_weights=bids(desc="iFOD2", suffix="tckWeights", ext=".txt").to_path().name,
        out_mu=bids(desc="iFOD2", suffix="muCoefficient", ext=".txt").to_path().name,
        nthreads=cfg["opt.threads"],
    )

    # Save relevant outputs
    logger.info("Saving relevant output files from tractography generation")
    out_dir = cfg["output_dir"].joinpath(bids(datatype="dwi").to_path().parent)
    utils.save(files=tckgen.tracks, out_dir=out_dir)
    utils.save(files=[tcksift.out_weights, tcksift.out_mu], out_dir=out_dir)
