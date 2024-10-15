"""Sub-module containing general optional arguments."""

from bidsapp_helper.parser import BidsAppArgumentParser


def add_index_args(app_parser: BidsAppArgumentParser) -> None:
    """Index analysis-level arguments."""
    index_args = app_parser.add_argument_group("index analysis-level options")
    index_args.add_argument(
        "--overwrite",
        dest="index.overwrite",
        action="store_true",
        help="overwrite previous index (default: %(default)s)",
    )
