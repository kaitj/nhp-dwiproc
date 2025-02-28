"""Utilities for working with directly with assets."""

from pathlib import Path

import nibabel.nifti1 as nib
from styxdefs import LocalRunner, get_global_runner
from styxdocker import DockerRunner
from styxgraph import GraphRunner
from styxsingularity import SingularityRunner

try:
    import nifti

    HAVE_NIFTI = True
except ImportError:
    HAVE_NIFTI = False


def load_nifti(fpath: str | Path) -> nib.Nifti1Image | nib.Nifti1Pair:
    """Load nifti using available library."""
    fpath = str(fpath)
    if HAVE_NIFTI:
        hdr, arr = nifti.read_volume(fpath)  # type: ignore

        # Transfer known header fields
        new_hdr = nib.Nifti1Header()
        for key, val in hdr.items():
            if key in new_hdr:
                new_hdr[key] = val

        aff = new_hdr.get_best_affine()
        return nib.Nifti1Image(dataobj=arr, affine=aff, header=new_hdr)

    return nib.load(fpath)


def gen_hash() -> str:
    """Generate styx runner hash for python code."""
    runner = get_global_runner()  # type: ignore
    if isinstance(runner, GraphRunner):
        runner: LocalRunner | DockerRunner | SingularityRunner = runner.base  # type: ignore

    runner.execution_counter += 1
    return f"{runner.uid}_{runner.execution_counter - 1}_python"
