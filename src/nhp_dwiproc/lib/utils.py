"""Utility functions for working with library sub module."""

from pathlib import Path

import nibabel as nib
from styxdefs import get_global_runner

try:
    import nifti

    HAVE_NIFTI = True
except ImportError:
    HAVE_NIFTI = False


def load_nifti(fpath: str | Path) -> nib.nifti1.Nifti1Image:
    """Helper to load nifti using available library."""
    if HAVE_NIFTI:
        hdr, arr = nifti.read_volume(str(fpath))
        new_hdr = nib.nifti1.Nifti1Header()
        for key, val in hdr.items():
            if key in new_hdr:
                new_hdr[key] = val
        aff = new_hdr.get_best_affine()
        return nib.nifti1.Nifti1Image(dataobj=arr, affine=aff, header=new_hdr)
    else:
        return nib.loadsave.load(fpath)


def gen_hash() -> str:
    """Generate a hash using the current date/time."""
    runner = get_global_runner()
    runner.base.execution_counter += 1

    hash = f"{runner.base.uid}_{runner.base.execution_counter - 1}_python"

    return hash
