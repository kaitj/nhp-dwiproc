"""Generation of connectivity files."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix

from nhp_dwiproc.app import utils


def generate_conn_matrix(
    input_data: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> None:
    """Generate connectivity matrix."""
    logger.info("Generating connectivity matrices")
    bids = partial(
        utils.bids_name,
        datatype="dwi",
        **input_group,
    )
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
                meas=meas,
                desc="probabilisticTracking",
                suffix="relmap",
                ext=".csv",
            ),
            assignment_radial_search=cfg["participant.connectivity.radius"],
            out_assignments=bids(
                desc="assignment",
                suffix="tractography",
                ext=".txt",
            ),
            tck_weights_in=tck_weights,
            scale_length=length,
            nthreads=cfg["opt.threads"],
        )

        # Save outputs
        utils.save(
            files=tck2connectome[meas].connectome_out,
            out_dir=cfg["output_dir"].joinpath(bids(directory=True)),
        )
