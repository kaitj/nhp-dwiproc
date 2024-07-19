"""Initialize application module."""

import importlib.metadata as ilm

from . import analysis_levels, type, utils
from .cli import parser
from .descriptor import generate_descriptor
from .utils import initialize

__name__ = "nhp_dwiproc"
__version__ = ilm.version(__name__)

__all__ = [
    "__name__",
    "__version__",
    "analysis_levels",
    "generate_descriptor",
    "initialize",
    "parser",
    "type",
    "utils",
]
