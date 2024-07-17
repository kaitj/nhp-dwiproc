"""Module related to directly updating application."""

import importlib.metadata as ilm
import pathlib as pl

from bidsapp_helper.descriptor import BidsAppDescriptor
from bidsapp_helper.parser import BidsAppArgumentParser

APP_NAME = "nhp_dwiproc"


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
    app_parser.parser.add_argument(
        "--runner",
        metavar="runner",
        type=str,
        default=None,
        choices=[None, "Docker", "Singularity", "Apptainer"],
        help="workflow runner to use (one of [%(choices)s]; default: %(default)s)",
    )
    app_parser.parser.add_argument(
        "--working-dir",
        "--working_dir",
        metavar="directory",
        dest="working_dir",
        default=None,
        type=pl.Path,
        help="working directory to temporarily write to (default: %(default)s)",
    )
    app_parser.parser.add_argument(
        "--container-config",
        "--container_config",
        metavar="config",
        dest="container_config",
        default=None,
        help="YAML config file mapping containers to 'local' paths",
    )
    app_parser.parser.add_argument(
        "--threads",
        metavar="threads",
        type=int,
        default=1,
        help="number of threads to use (default: %(default)d).",
    )
    app_parser.parser.add_argument(
        "--index-path",
        "--index_path",
        metavar="path",
        dest="index_path",
        type=pl.Path,
        default=None,
        help="bids2table index path (default: {bids_dir}/index.b2t)",
    )
    app_parser.parser.add_argument(
        "--b0-thresh",
        "--b0_thresh",
        metavar="thresh",
        dest="b0_thresh",
        type=int,
        default=10,
        help="threshold for shell to be considered b=0 (default: %(default)d)",
    )


def _add_index_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with index analysis-level."""
    index_args = app_parser.parser.add_argument_group("index analysis-level soptions")
    index_args.add_argument(
        "--overwrite",
        dest="index_overwrite",
        action="store_true",
        help="overwrite previous index (default: %(default)s)",
    )


def _add_participant_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with participant analysis-level."""
    participant_args = app_parser.parser.add_argument_group(
        "participant analysis-level options"
    )
    participant_args.add_argument(
        "--participant-query",
        "--participant_query",
        metavar="query",
        dest="participant_query",
        type=str,
        help="string query with bids entities for specific participants",
    )
    participant_args.add_argument(
        "--single-shell",
        "--single_shell",
        dest="single_shell",
        action="store_true",
        help="Process single-shell data (default: %(default)s)",
    )
    participant_args.add_argument(
        "--shells",
        metavar="shell",
        dest="shells",
        nargs="*",
        type=int,
        help="space-separated list of b-values (b=0 must be included explicitly)",
    )
    participant_args.add_argument(
        "--lmax",
        metavar="lmax",
        nargs="*",
        type=int,
        help="""maximum harmonic degree(s)
        (space-separated for multiple b-values, b=0 must be included explicitly)
        """,
    )
    participant_args.add_argument(
        "--steps",
        metavar="steps",
        dest="tractography_steps",
        type=float,
        help="Step size (in mm) for tractography",
    )
    participant_args.add_argument(
        "--streamlines",
        metavar="streamlines",
        dest="tractography_streamlines",
        type=int,
        default=10000,
        help="Number of streamlines to select (default %(default)d)",
    )


def pipeline_descriptor(out_fpath: pl.Path) -> None:
    """Generator and save app descriptor."""
    descriptor = BidsAppDescriptor(
        app_name=APP_NAME,
        bids_version="1.9.0",
        app_version=ilm.version("nhp_dwiproc"),
        repo_url="https://github.com/kaitj/nhp-dwiproc",
        author="Jason Kai",
        author_email="jason.kai@childmind.org",
    )
    descriptor.save(out_fpath)
