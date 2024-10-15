"""Initialize different analysis-level arguments."""

from nhp_dwiproc.app.cli.args.connectivity import add_connectivity_args
from nhp_dwiproc.app.cli.args.index import add_index_args
from nhp_dwiproc.app.cli.args.optional import add_optional_args
from nhp_dwiproc.app.cli.args.preprocess import add_preprocess_args
from nhp_dwiproc.app.cli.args.tractography import add_tractography_args

__all__ = [
    "add_connectivity_args",
    "add_optional_args",
    "add_index_args",
    "add_preprocess_args",
    "add_tractography_args",
]
