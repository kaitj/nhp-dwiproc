"""Sub-module containing connectivity optional arguments."""

from bidsapp_helper.parser import BidsAppArgumentParser


def add_connectivity_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with Connectivity analysis-level arguments."""
    connectivity_args = app_parser.add_argument_group(
        "connectivity analysis-level options",
    )
    connectivity_args.add_argument(
        "--atlas",
        metavar="atlas",
        dest="participant.connectivity.atlas",
        type=str,
        default=None,
        help="volumetric atlas name (assumed to be processed) for connectivity matrix",
    )
    connectivity_args.add_argument(
        "--radius",
        metavar="radius",
        dest="participant.connectivity.radius",
        type=float,
        default=2,
        help="distance (in mm) to map to nearest parcel (default: %(default).2f)",
    )
