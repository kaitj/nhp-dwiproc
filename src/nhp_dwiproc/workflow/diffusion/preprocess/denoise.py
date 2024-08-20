"""Steps associated with denoising."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix
from styxdefs import OutputPathType

from ....app import utils


def denoise(
    input_data: dict[str, Any], bids: partial, cfg: dict[str, Any], logger: Logger
) -> OutputPathType:
    """Perform mrtrix denoising."""
    logger.info("Performing denoising")

    if cfg["participant.preproc.denoise.skip"]:
        return input_data["dwi"]["nii"]

    denoise = mrtrix.dwidenoise(
        dwi=input_data["dwi"]["nii"],
        out=bids(
            desc="denoise",
            suffix="dwi",
            ext=".nii.gz",
        )
        .to_path()
        .name,
        estimator=cfg["participant.preproc.denoise.estimator"],
        noise=bids(
            extra_entities={
                "algorithm": cfg["participant.preproc.denoise.estimator"],
                "param": "noise",
            },
            suffix="dwimap",
            ext=".nii.gz",
        )
        if (noise_map := cfg["participant.preproc.denoise.map"])
        else None,
        extent=cfg["participant.preproc.denoise.extent"],
        nthreads=cfg["opt.threads"],
    )

    if noise_map:
        utils.save(
            files=denoise.noise,
            out_dir=cfg["output_dir"].joinpath(bids(datatype="dwi").to_path().parent),
        )

    return denoise.out
