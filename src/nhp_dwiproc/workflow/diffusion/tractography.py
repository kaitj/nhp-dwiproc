"""Tractography-related operations."""

from functools import partial
from pathlib import Path

import niwrap_helper
from niwrap import mrtrix

import nhp_dwiproc.utils as utils


def generate_tractography(
    dwi_5tt: Path | None,
    method: str,
    fod: mrtrix.MtnormaliseOutputs,
    steps: float | None,
    cutoff: float | None,
    streamlines: int,
    maxlength: float | None,
    backtrack: bool,
    nocrop_gmwmi: bool,
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    output_fpath: Path = Path.cwd(),
) -> None:
    """Generate subject tractography."""
    tckgen_params = {
        "source": (wm_fod := fod.input_output[0].output),
        "tracks": bids(method="iFOD2", suffix="tractography", ext=".tck"),
        "algorithm": "iFOD2",
        "seed_dynamic": wm_fod,
        "step": steps,
        "cutoff": cutoff,
        "select_": streamlines,
        "maxlength": maxlength,
    }
    if method == "act":
        tckgen_params.update(
            {
                "act": dwi_5tt,
                "backtrack": backtrack,
                "crop_at_gmwmi": not nocrop_gmwmi,
            }
        )
    tckgen = mrtrix.tckgen(**tckgen_params)
    tcksift = mrtrix.tcksift2(
        in_tracks=tckgen.tracks,
        in_fod=wm_fod,
        out_weights=bids(method="SIFT2", suffix="tckWeights", ext=".txt"),
    )

    tdi = {}
    for meas, weights in zip(["raw", "weighted"], [None, tcksift.out_weights]):
        tdi[meas] = mrtrix.tckmap(
            tracks=tckgen.tracks,
            tck_weights_in=weights,
            template=wm_fod,
            output=bids(meas=meas, suffix="tdi", ext=".nii.gz"),
        )

    # Save relevant outputs
    utils.io.save(
        files=[tckgen.tracks, tcksift.out_weights, tdi["weighted"].output],
        out_dir=output_fpath,
    )
