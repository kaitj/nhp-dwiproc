"""Tractography generation."""

from argparse import Namespace
from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix

from ...app import utils


def generate_tractography(
    input_data: dict[str, Any],
    fod: mrtrix.MtnormaliseOutputs,
    bids: partial,
    args: Namespace,
    logger: Logger,
) -> None:
    """Generate subject tractography."""
    logger.info("Generating tractography")
    tckgen = mrtrix.tckgen(
        source=fod.input_output[0].output,
        tracks=bids(desc="iFOD2", suffix="tractography", ext=".tck"),
        mask=input_data["dwi"]["mask"],
        seed_image=input_data["dwi"]["mask"],
        algorithm="iFOD2",
        step=args.tractography_steps if args.tractography_steps else None,
        select_=args.streamline_count,
        nthreads=args.nthreads,
    )

    logger.info("Computing per-streamline multipliers")
    tcksift = mrtrix.tcksift2(
        in_tracks=tckgen.tracks,
        in_fod=fod.input_output[0].output,
        out_weights=bids(desc="iFOD2", suffix="tckWeights", ext=".txt"),
        out_mu=bids(desc="iFOD2", suffix="muCoefficient", ext=".txt"),
        nthreads=args.nthreads,
    )

    # Save relevant outputs
    logger.info("Saving relevant output files from tractography generation")
    out_dir = args.out_dir.joinpath(bids(datatype="dwi").to_path().parent)
    utils.save(files=tckgen.tracks, out_dir=out_dir)
    utils.save(files=[tcksift.out_weights, tcksift.out_mu], out_dir=out_dir)
