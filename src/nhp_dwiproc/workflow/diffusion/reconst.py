"""Processing of diffusion data to setup tractography."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix

from ...app import utils


def compute_fods(
    input_data: dict[str, Any],
    bids: partial,
    cfg: dict[str, Any],
    logger: Logger,
) -> mrtrix.MtnormaliseOutputs:
    """Process subject for tractography."""
    logger.info("Computing response function")
    dwi2response = mrtrix.dwi2response(
        algorithm=mrtrix.Dwi2responseDhollander(
            input_=input_data["dwi"]["nii"],
            out_sfwm=bids(desc="wm", suffix="response", ext=".txt").to_path().name,
            out_gm=bids(desc="gm", suffix="response", ext=".txt").to_path().name,
            out_csf=bids(desc="csf", suffix="response", ext=".txt").to_path().name,
        ),
        fslgrad=mrtrix.Dwi2responseFslgrad(
            bvecs=input_data["dwi"]["bvec"],
            bvals=input_data["dwi"]["bval"],
        ),
        mask=input_data["dwi"]["mask"],
        shells=shells if (shells := cfg["participant.shells"]) else None,
        lmax=lmax if (lmax := cfg["participant.lmax"]) else None,
        nthreads=cfg["opt.threads"],
        config=[
            mrtrix.Dwi2responseConfig(
                "BZeroThreshold", (b0_thresh := str(cfg["participant.b0_thresh"]))
            )
        ],
    )

    logger.info("Computing fiber orientation distribution")
    response_odf = [
        mrtrix.Dwi2fodResponseOdf(
            dwi2response.algorithm.out_sfwm,
            bids(desc="wm", suffix="fod", ext=".mif").to_path().name,
        ),
        mrtrix.Dwi2fodResponseOdf(
            dwi2response.algorithm.out_gm,
            bids(desc="gm", suffix="fod", ext=".mif").to_path().name,
        ),
        mrtrix.Dwi2fodResponseOdf(
            dwi2response.algorithm.out_csf,
            bids(desc="csf", suffix="fod", ext=".mif").to_path().name,
        ),
    ]
    if cfg["participant.single_shell"]:
        logger.info("Leaving out GM for single-shell computation")
        response_odf = [response_odf[0], response_odf[2]]
    dwi2fod = mrtrix.dwi2fod(
        algorithm="msmt_csd",
        dwi=input_data["dwi"]["nii"],
        response_odf=response_odf,
        fslgrad=mrtrix.Dwi2fodFslgrad(
            bvecs=input_data["dwi"]["bvec"],
            bvals=input_data["dwi"]["bval"],
        ),
        mask=input_data["dwi"]["mask"],
        shells=shells if shells else None,
        nthreads=cfg["opt.threads"],
        config=[mrtrix.Dwi2fodConfig("BZeroThreshold", b0_thresh)],
    )

    logger.info("Normalizing fiber orientation distributions")
    normalize_odf = [
        mrtrix.MtnormaliseInputOutput(
            tissue_odf.odf, tissue_odf.odf.name.replace("fod", "fodNorm")
        )
        for tissue_odf in dwi2fod.response_odf
    ]
    mtnormalise = mrtrix.mtnormalise(
        input_output=normalize_odf,
        mask=input_data["dwi"]["mask"],
        nthreads=cfg["opt.threads"],
    )

    # Save relevant outputs
    logger.info("Saving relevant output files from reconstruction")
    mtnormalise_output = [
        mtnormalise_output.output for mtnormalise_output in mtnormalise.input_output
    ]
    utils.save(
        files=mtnormalise_output,
        out_dir=cfg["output_dir"].joinpath(bids(datatype="dwi").to_path().parent),
    )

    return mtnormalise
