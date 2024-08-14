"""Generation of connectivity files."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix

from ...app import utils


def generate_conn_matrix(
    input_data: dict[str, Any],
    bids: partial,
    cfg: dict[str, Any],
    logger: Logger,
) -> None:
    """Generate connectivity matrix."""
    logger.info("Generating connectivity matrices")

    tck2connectome = {}
    for meas, tck_weights, length in zip(
        ["afd", "count", "avgLength"],
        [input_data["tractography"]["weights"], None, None],
        [False, False, True],
    ):
        tck2connectome[meas] = mrtrix.tck2connectome(
            tracks_in=input_data["tractography"]["tck"],
            nodes_in=input_data["atlas"],
            connectome_out=bids(
                extra_entities={"meas": meas},
                desc="probabilisticTracking",
                suffix="relmap",
                ext=".csv",
            )
            .to_path()
            .name,
            assignment_radial_search=cfg["participant.connectivity.radius"],
            out_assignments=bids(desc="assignment", suffix="tractography", ext=".txt")
            .to_path()
            .name,
            tck_weights_in=tck_weights,
            scale_length=length,
            nthreads=cfg["opt.threads"],
        )

        # Save outputs
        utils.save(
            files=tck2connectome[meas].connectome_out,
            out_dir=cfg["output_dir"].joinpath(bids(datatype="dwi").to_path().parent),
        )
