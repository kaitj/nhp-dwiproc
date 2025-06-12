"""Functions for manipulating anatomical images."""

from functools import partial
from pathlib import Path

import nibabel.nifti1 as nib
import niwrap_helper
import numpy as np

import nhp_dwiproc.utils as utils


def fake_t2w(
    t1w: Path,
    bids: partial = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: Path = Path.cwd() / "tmp",
) -> Path:
    """Fake T2w contrast from T1w."""
    t1w_nii = utils.assets.load_nifti(fpath=t1w)
    t2w_dataobj = -np.array(t1w_nii.dataobj) + np.max(t1w_nii.dataobj)
    t2w_nii = nib.Nifti1Image(
        dataobj=t2w_dataobj, affine=t1w_nii.affine, header=t1w_nii.header
    )
    t2w_fname = bids(desc="fake", suffix="T2w", ext=".nii.gz")
    t2w_fpath: Path = output_dir / f"{utils.assets.gen_hash()}_fake-t2w" / t2w_fname
    t2w_fpath.parent.mkdir(parents=True, exist_ok=False)
    nib.save(img=t2w_nii, filename=t2w_fpath)

    return t2w_fpath
