"""Module related to directly updating application."""

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
    return app_parser


def _add_optional_args(app_parser: BidsAppArgumentParser) -> None:
    """General optional arguments."""
    app_parser.parser.add_argument(
        "-N",
        "--threads",
        metavar="threads",
        type=int,
        default=1,
        help="number of threads to use (default: %(default)d).",
    )
    app_parser.parser.add_argument(
        "--participant-query",
        "--participant_query",
        metavar="participant_query",
        type=str,
        help="string query with bids entities for specific participants",
    )


def _add_index_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with index analysis-level."""
    index_args = app_parser.parser.add_argument_group("index-level optional arguments")
    index_args.add_argument(
        "--index-path",
        "--index_path",
        metavar="path",
        dest="index_path",
        type=pl.Path,
        default=None,
        help="bids2table index path (default: {bids_dir}/index.b2t)",
    )
    index_args.add_argument(
        "-x",
        "--overwrite",
        dest="index_overwrite",
        action="store_true",
        help="overwrite previous index (default: %(default)s)",
    )


def descriptor(out_fpath: pl.Path) -> None:
    """Generator and save app descriptor."""
    descriptor = BidsAppDescriptor(
        app_name=APP_NAME,
        bids_version="1.9.0",
        app_version="0.1.0",
        repo_url="https://github.com/kaitj/nhp-dwiproc",
        author="Jason Kai",
        author_email="jason.kai@childmind.org",
    )
    descriptor.save(out_fpath)
