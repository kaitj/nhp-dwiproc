"""Processing of diffusion data to setup tractography."""

from argparse import Namespace
from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix


def compute_subj_fods(
    input_data: dict[str, Any],
    bids: partial,
    args: Namespace,
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
        shells=args.shells if args.shells else None,
        lmax=args.lmax if args.lmax else None,
        nthreads=args.nthreads,
        config=[mrtrix.Dwi2responseConfig("BZeroThreshold", args.b0_thresh)],
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
    if args.single_shell:
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
        shells=args.shells if args.shells else None,
        nthreads=args.nthreads,
        config=[mrtrix.Dwi2fodConfig("BZeroThreshold", args.b0_thresh)],
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
        nthreads=args.nthreads,
    )

    return mtnormalise
