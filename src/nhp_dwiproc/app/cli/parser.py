"""Main entry point for CLI parser."""

from bidsapp_helper.parser import BidsAppArgumentParser

from nhp_dwiproc.app.cli import args
from nhp_dwiproc.app.utils import APP_NAME


def parser() -> BidsAppArgumentParser:
    """Initialize and update parser."""
    app_parser = BidsAppArgumentParser(
        app_name=APP_NAME,
        description="Diffusion processing NHP data.",
    )
    app_parser.update_analysis_level(
        ["index", "preprocess", "tractography", "connectivity"]
    )
    args.add_optional_args(app_parser=app_parser)
    args.add_index_args(app_parser=app_parser)
    args.add_preprocess_args(app_parser=app_parser)
    args.add_tractography_args(app_parser=app_parser)
    args.add_connectivity_args(app_parser=app_parser)
    return app_parser
