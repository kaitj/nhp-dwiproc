"""Utility functions for working with library sub module."""

from styxdefs import get_global_runner


def gen_hash() -> str:
    """Generate a hash using the current date/time."""
    runner = get_global_runner()
    runner.base.execution_counter += 1

    hash = f"{runner.base.uid}_{runner.base.execution_counter - 1}_python"

    return hash
