"""Preprocess steps associated with bias correction."""

from functools import partial
from pathlib import Path

from niwrap import mrtrix

import nhp_dwiproc.utils as utils


def biascorrect(
    dwi: Path,
    bval: Path,
    bvec: Path,
    spacing: float,
    iters: float,
    shrink: float,
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
    output_dir: Path = Path.cwd(),
) -> tuple[Path, ...]:
    """Perform biascorrection steps."""
    dwibiascorrect = partial(
        mrtrix.dwibiascorrect,
        algorithm="ants",
        fslgrad=mrtrix.dwibiascorrect_fslgrad_params(bvecs=bvec, bvals=bval),
        ants_b=f"{spacing},3",
        ants_c=f"{iters},0.0",
        ants_s=f"{shrink}",
    )

    biascorrect = dwibiascorrect(
        input_image=dwi,
        output_image=bids(desc="biascorrect", suffix="dwi", ext=".nii.gz"),
    )
    biascorrect = dwibiascorrect(
        input_image=biascorrect.output_image_file,
        output_image=bids(desc="preproc", suffix="dwi", ext=".nii.gz"),
    )
    utils.io.save(files=biascorrect.output_image_file, out_dir=output_dir)

    mask = mrtrix.dwi2mask(
        input_=biascorrect.output_image_file,
        output=bids(desc="biascorrect", suffix="mask", ext=".nii.gz"),
        fslgrad=mrtrix.dwi2mask_fslgrad_params(bvecs=bvec, bvals=bval),
    )

    return biascorrect.output_image_file, mask.output
