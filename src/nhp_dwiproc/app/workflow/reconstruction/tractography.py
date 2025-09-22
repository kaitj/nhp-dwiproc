"""Tractography-related operations."""

from functools import partial
from pathlib import Path

from niwrap import mrtrix
from niwrap_helper import bids_path, save


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
    bids: partial[str] = partial(bids_path, sub="subject"),
    output_fpath: Path = Path.cwd(),
) -> None:
    """Sub-workflow for tractography processing.

    Args:
        dwi_5tt: Path to 5-tissue type image, if ACT is used.
        method: Algorithm to perform.
        fod: Fibre orientation distributions.
        steps: Sampling step size.
        cutoff: FOD cutoff threshold.
        streamlines: Number of streamlines to generate.
        backtrack: Flag to indicate backtracking, if ACT is used.
        nocrop_gmwmi: Flag to indicate to not crop at GM-WM interface, if ACT is used.
        bids: Function to generate BIDS filepath.
        output_fpath: Output directory.
    """
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
    save(
        files=[tckgen.tracks, tcksift.out_weights, tdi["weighted"].output],
        out_dir=output_fpath,
    )
