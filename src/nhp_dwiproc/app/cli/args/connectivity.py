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
    connectivity_args.add_argument(
        "--vox-mm",
        "--vox_mm",
        metavar="voxel_size",
        dest="participant.connectivity.vox_mm",
        type=float,
        nargs="*",
        default=None,
        help="""isotropic voxel size (in mm) or space-separated listed of voxel sizes to
        map tracts to""",
    )
    connectivity_args.add_argument(
        "--tract-query",
        "--tract_query",
        metavar="query",
        dest="participant.connectivity.query_tract",
        type=str,
        default=None,
        help="""string query for bids entities associated with tract (subject & session
        is assumed);  associated ROIs should be part of dataset descriptions that
        contain 'include', 'exclude', 'stop' keywords for respective ROIs.""",
    )
    connectivity_args.add_argument(
        "--surf-query",
        "--surf_query",
        metavar="query",
        dest="participant.connectivity.query_surf",
        type=str,
        default=None,
        help="""string query for bids entities associated with surfaces to perform
        ribbon constrained mapping of streamlines to (subject & session is assumed);
        surface type (e.g. white, pial, etc.) will be automatically identified""",
    )
