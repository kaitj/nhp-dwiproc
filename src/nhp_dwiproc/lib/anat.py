"""Functions for manipulating anatomical images."""

from functools import partial
from pathlib import Path
from typing import Any

import nibabel.nifti1 as nib
import numpy as np
from styxdefs import InputPathType

import nhp_dwiproc.utils as utils


def fake_t2w(
    t1w: InputPathType, input_group: dict[str, Any], cfg: dict[str, Any]
) -> Path:
    """Fake T2w contrast from T1w."""
    bids = partial(utils.io.bids_name, datatype="anat", **input_group)

    t1w_nii = utils.assets.load_nifti(fpath=t1w)
    t2w_dataobj = -np.array(t1w_nii.dataobj) + np.max(t1w_nii.dataobj)
    t2w_nii = nib.Nifti1Image(
        dataobj=t2w_dataobj, affine=t1w_nii.affine, header=t1w_nii.header
    )
    t2w_fname = bids(desc="fake", suffix="T2w", ext=".nii.gz")
    t2w_fpath: Path = (
        cfg["opt.working_dir"] / f"{utils.assets.gen_hash()}_fake-t2w" / t2w_fname
    )
    t2w_fpath.parent.mkdir(parents=True, exist_ok=False)
    nib.save(img=t2w_nii, filename=t2w_fpath)

    return t2w_fpath
