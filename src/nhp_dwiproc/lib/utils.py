"""Utility functions for working with library sub module."""

import hashlib
from datetime import datetime


def gen_hash() -> str:
    """Generate a hash using the current date/time."""
    cur_time = datetime.now().isoformat().encode("utf-8")
    hash = hashlib.sha256(cur_time)

    return hash.hexdigest()
