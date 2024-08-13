"""Application command-line interface."""

import pathlib as pl

from bidsapp_helper.parser import BidsAppArgumentParser

from .utils import APP_NAME


def parser() -> BidsAppArgumentParser:
    """Initialize and update parser."""
    app_parser = BidsAppArgumentParser(
        app_name=APP_NAME, description="Diffusion processing NHP data."
    )
    app_parser.update_analysis_level(["index", "participant"])
    _add_optional_args(app_parser=app_parser)
    _add_index_args(app_parser=app_parser)
    _add_participant_args(app_parser=app_parser)
    return app_parser


def _add_optional_args(app_parser: BidsAppArgumentParser) -> None:
    """General optional arguments."""
    app_parser.add_argument(
        "--runner",
        metavar="runner",
        dest="opt.runner",
        type=str,
        default=None,
        choices=[None, "Docker", "Singularity", "Apptainer"],
        help="workflow runner to use (one of [%(choices)s]; default: %(default)s)",
    )
    app_parser.add_argument(
        "--working-dir",
        "--working_dir",
        metavar="directory",
        dest="opt.working_dir",
        default="styx_tmp",
        type=pl.Path,
        help="working directory to temporarily write to (default: %(default)s)",
    )
    app_parser.add_argument(
        "--container-config",
        "--container_config",
        metavar="config",
        dest="opt.containers",
        default=None,
        type=pl.Path,
        help="YAML config file mapping containers to 'local' paths",
    )
    app_parser.add_argument(
        "--threads",
        metavar="threads",
        dest="opt.threads",
        type=int,
        default=1,
        help="number of threads to use (default: %(default)d)",
    )
    app_parser.add_argument(
        "--seed-num",
        "--seed_num",
        metavar="seed_num",
        dest="opt.seed_num",
        type=int,
        default=99,
        help="fixed seed for reproducible results (default: %(default)d)",
    )
    app_parser.add_argument(
        "--index-path",
        "--index_path",
        metavar="path",
        dest="opt.index_path",
        type=pl.Path,
        default=None,
        help="bids2table index path (default: {bids_dir}/index.b2t)",
    )
    app_parser.add_argument(
        "--graph",
        dest="opt.graph",
        action="store_true",
        help="Print diagram of workflow",
    )


def _add_index_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with index analysis-level."""
    index_args = app_parser.add_argument_group("index analysis-level soptions")
    index_args.add_argument(
        "--overwrite",
        dest="index.overwrite",
        action="store_true",
        help="overwrite previous index (default: %(default)s)",
    )


def _add_participant_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with participant analysis-level."""
    participant_args = app_parser.add_argument_group(
        "participant analysis-level options"
    )
    participant_args.add_argument(
        "--participant-query",
        "--participant_query",
        metavar="query",
        dest="participant.query",
        type=str,
        help="string query with bids entities for specific participants",
    )
    app_parser.add_argument(
        "--b0-thresh",
        "--b0_thresh",
        metavar="thresh",
        dest="participant.b0_thresh",
        type=int,
        default=10,
        help="threshold for shell to be considered b=0 (default: %(default)d)",
    )
    participant_args.add_argument(
        "--single-shell",
        "--single_shell",
        dest="participant.single_shell",
        action="store_true",
        help="Process single-shell data (default: %(default)s)",
    )
    participant_args.add_argument(
        "--shells",
        metavar="shell",
        dest="participant.shells",
        nargs="*",
        type=int,
        help="space-separated list of b-values (b=0 must be included explicitly)",
    )
    participant_args.add_argument(
        "--lmax",
        metavar="lmax",
        dest="participant.lmax",
        nargs="*",
        type=int,
        help="""maximum harmonic degree(s)
        (space-separated for multiple b-values, b=0 must be included explicitly)
        """,
    )
    participant_args.add_argument(
        "--steps",
        metavar="steps",
        dest="participant.tractography.steps",
        type=float,
        help="step size (in mm) for tractography (default: 0.5 x voxel size)",
    )
    participant_args.add_argument(
        "--cutoff",
        metavar="cutoff",
        dest="participant.tractography.cutoff",
        type=float,
        default=0.1,
        help="cutoff FOD amplitude value for terminating tracks (default: %(default)f)",
    )
    participant_args.add_argument(
        "--streamlines",
        metavar="streamlines",
        dest="participant.tractography.streamlines",
        type=int,
        default=10_000,
        help="number of streamlines to select (default %(default)d)",
    )
    participant_args.add_argument(
        "--atlas",
        metavar="atlas",
        dest="participant.connectivity.atlas",
        type=str,
        default=None,
        help="volumetric atlas name (assumed to be processed) for connectivity matrix",
    )
