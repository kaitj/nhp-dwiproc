"""Processing of diffusion data to setup tractography."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix

from nhp_dwiproc.app import utils


def compute_fods(
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> mrtrix.MtnormaliseOutputs:
    """Process subject for tractography."""
    logger.info("Computing response function")
    bids = partial(
        utils.bids_name,
        datatype="dwi",
        method="dhollander",
        suffix="response",
        ext=".txt",
        **input_data["entities"],
    )
    dwi2response = mrtrix.dwi2response(
        algorithm=mrtrix.Dwi2responseDhollander(
            input_=input_data["dwi"]["nii"],
            out_sfwm=bids(param="wm"),
            out_gm=bids(param="gm"),
            out_csf=bids(param="csf"),
        ),
        fslgrad=mrtrix.Dwi2responseFslgrad(
            bvecs=input_data["dwi"]["bvec"],
            bvals=input_data["dwi"]["bval"],
        ),
        mask=input_data["dwi"]["mask"],
        shells=shells if (shells := cfg["participant.tractography.shells"]) else None,
        lmax=lmax if (lmax := cfg["participant.tractography.lmax"]) else None,
        nthreads=cfg["opt.threads"],
        config=[
            mrtrix.Dwi2responseConfig(
                "BZeroThreshold", (b0_thresh := str(cfg["participant.b0_thresh"]))
            )
        ],
    )

    logger.info("Computing fiber orientation distribution")
    bids = partial(
        utils.bids_name,
        datatype="dwi",
        model="csd",
        suffix="dwimap",
        ext=".mif",
        **input_data["entities"],
    )
    response_odf = [
        mrtrix.Dwi2fodResponseOdf(
            dwi2response.algorithm.out_sfwm,
            bids(param="wm"),
        ),
        mrtrix.Dwi2fodResponseOdf(
            dwi2response.algorithm.out_gm,
            bids(param="gm"),
        ),
        mrtrix.Dwi2fodResponseOdf(
            dwi2response.algorithm.out_csf,
            bids(param="csf"),
        ),
    ]
    if cfg["participant.tractography.single_shell"]:
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
            tissue_odf.odf,
            tissue_odf.odf.name.replace("dwimap.mif", "desc-normalized_dwimap.mif"),
        )
        for tissue_odf in dwi2fod.response_odf
    ]
    mtnormalise = mrtrix.mtnormalise(
        input_output=normalize_odf,
        mask=input_data["dwi"]["mask"],
        nthreads=cfg["opt.threads"],
    )

    return mtnormalise


def compute_dti(
    input_data: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> None:
    """Process diffusion tensors."""
    logger.info("Performing tensor fitting")
    bids = partial(
        utils.bids_name(
            datatype="dwi",
            model="tensor",
            suffix="dwimap",
            ext=".nii.gz",
            **input_data["entities"],
        )
    )
    dwi2tensor = mrtrix.dwi2tensor(
        dwi=input_data["dwi"]["nii"],
        dt=bids(),
        fslgrad=mrtrix.Dwi2tensorFslgrad(
            bvecs=input_data["dwi"]["bvec"],
            bvals=input_data["dwi"]["bval"],
        ),
        mask=input_data["dwi"]["mask"],
        nthreads=cfg["opt.threads"],
        config=[
            mrtrix.Dwi2tensorConfig(
                "BZeroThreshold", (b0_thresh := str(cfg["participant.b0_thresh"]))
            )
        ],
    )

    logger.info("Generating tensor maps")
    tensor2metrics = mrtrix.tensor2metric(
        tensor=dwi2tensor.dt,
        mask=input_data["dwi"]["mask"],
        adc=bids(param="MD"),
        fa=bids(param="FA"),
        rd=bids(param="RD"),
        ad=bids(param="AD"),
        value=bids(param="S1"),
        vector=bids(param="V1"),
        num=[1],
        nthreads=cfg["opt.threads"],
        config=[mrtrix.Tensor2metricConfig("BZeroThreshold", b0_thresh)],
    )

    # Save relevant outputs
    utils.io.save(
        files=[
            tensor2metrics.adc,
            tensor2metrics.fa,
            tensor2metrics.ad,
            tensor2metrics.rd,
            tensor2metrics.value,
            tensor2metrics.vector,
        ],
        out_dir=cfg["output_dir"].joinpath(
            utils.bids_name(directory=True, datatype="dwi", **input_data["entities"])
        ),
    )
