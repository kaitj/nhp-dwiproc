"""Sub-module containing tractography optional arguments."""

from bidsapp_helper.parser import BidsAppArgumentParser


def add_tractography_args(app_parser: BidsAppArgumentParser) -> None:
    """Tractography analysis-level arguments."""
    tractography_args = app_parser.add_argument_group(
        "tractography analysis-level options",
    )
    tractography_args.add_argument(
        "--single-shell",
        "--single_shell",
        dest="participant.tractography.single_shell",
        action="store_true",
        help="process single-shell data (default: %(default)s)",
    )
    tractography_args.add_argument(
        "--shells",
        metavar="shell",
        dest="participant.tractography.shells",
        nargs="*",
        type=int,
        help="space-separated list of b-values (b=0 must be included explicitly)",
    )
    tractography_args.add_argument(
        "--lmax",
        metavar="lmax",
        dest="participant.tractography.lmax",
        nargs="*",
        type=int,
        help="""maximum harmonic degree(s)
        (space-separated for multiple b-values, b=0 must be included explicitly)
        """,
    )
    tractography_args.add_argument(
        "--steps",
        metavar="steps",
        dest="participant.tractography.steps",
        type=float,
        help="step size (in mm) for tractography (default: 0.5 x voxel size)",
    )
    tractography_args.add_argument(
        "--tractography-method",
        "--tractography_method",
        metavar="method",
        dest="participant.tractography.method",
        type=str,
        default="wm",
        choices=["wm", "act"],
        help="tractography seeding method (one of [%(choices)s]; default: %(default)s)",
    )
    tractography_args.add_argument(
        "--cutoff",
        metavar="cutoff",
        dest="participant.tractography.cutoff",
        type=float,
        default=0.1,
        help="cutoff FOD amplitude for track termination (default: %(default).2f)",
    )
    tractography_args.add_argument(
        "--streamlines",
        metavar="streamlines",
        dest="participant.tractography.streamlines",
        type=int,
        default=10_000,
        help="number of streamlines to select (default %(default)d)",
    )
