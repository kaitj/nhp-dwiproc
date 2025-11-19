"""Preprocess steps associated with bias correction."""

from functools import partial
from pathlib import Path

import niwrap_helper
from niwrap import mrtrix

from nhp_dwiproc.config.preprocess import BiascorrectConfig


def biascorrect(
    dwi: Path,
    bval: Path,
    bvec: Path,
    biascorrect_opts: BiascorrectConfig = BiascorrectConfig(),
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    output_dir: Path = Path.cwd(),
) -> tuple[Path, ...]:
    """Perform biascorrection steps using the ANTs algorithm.

    Args:
        dwi: Diffusion nifti file path to process.
        bval: Diffusion associated bval file path.
        bvec: Diffusion associated bvec file path.
        biascorrect_opts: Biascorrect configuration options.
        bids: Function to generate BIDS file path.
        output_dir: Directory to save outputs to.

    Returns:
        A 2-tuple, with the biascorrected diffusion nifti and subsequent generated
        brain mask file paths.

    """
    dwibiascorrect = partial(
        mrtrix.dwibiascorrect,
        algorithm="ants",
        fslgrad=mrtrix.dwibiascorrect_fslgrad(bvecs=bvec, bvals=bval),
        ants_b=f"{biascorrect_opts.spacing},3",
        ants_c=f"{biascorrect_opts.iters},0.0",
        ants_s=f"{biascorrect_opts.shrink}",
    )
    biascorrect = dwibiascorrect(
        input_image=dwi,
        output_image=bids(desc="biascorrect", suffix="dwi", ext=".nii.gz"),
    )
    biascorrect = dwibiascorrect(
        input_image=biascorrect.output_image_file,
        output_image=bids(desc="preproc", suffix="dwi", ext=".nii.gz"),
    )
    niwrap_helper.save(files=biascorrect.output_image_file, out_dir=output_dir)

    mask = mrtrix.dwi2mask(
        input_=biascorrect.output_image_file,
        output=bids(desc="biascorrect", suffix="mask", ext=".nii.gz"),
        fslgrad=mrtrix.dwibiascorrect_fslgrad(bvecs=bvec, bvals=bval),
    )
    return biascorrect.output_image_file, mask.output
