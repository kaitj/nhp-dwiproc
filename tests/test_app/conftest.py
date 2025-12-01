from pathlib import Path

import pytest


@pytest.fixture
def ds_dir() -> Path:
    """Path to dummy dataset directory."""
    ds_dpath = Path("tests/data")
    if not ds_dpath.exists():
        raise FileNotFoundError("Dummy dataset not found")
    return ds_dpath
