"""Utility functions for working with library sub module."""

from pathlib import Path

import nibabel.nifti1 as nib
from styxdefs import get_global_runner

try:
    import nifti

    HAVE_NIFTI = True
except ImportError:
    HAVE_NIFTI = False


def load_nifti(fpath: str | Path) -> nib.Nifti1Image | nib.Nifti1Pair:
    """Helper to load nifti using available library."""
    if HAVE_NIFTI:
        hdr, arr = nifti.read_volume(str(fpath))  # type: ignore
        new_hdr = nib.Nifti1Header()
        for key, val in hdr.items():
            if key in new_hdr:
                new_hdr[key] = val
        aff = new_hdr.get_best_affine()
        return nib.Nifti1Image(dataobj=arr, affine=aff, header=new_hdr)
    else:
        return nib.load(fpath)


def gen_hash() -> str:
    """Generate a hash using the current date/time."""
    runner = get_global_runner()
    runner.base.execution_counter += 1  # type: ignore

    hash = f"{runner.base.uid}_{runner.base.execution_counter - 1}_python"  # type: ignore

    return hash
