"""Processing of diffusion data to setup tractography."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix, mrtrix3tissue

import nhp_dwiproc.utils as utils


def _create_response_odf(
    response: mrtrix.Dwi2responseDhollanderOutputs, bids: partial, single_shell: bool
) -> list[mrtrix.Dwi2fodResponseOdf | mrtrix3tissue.Ss3tCsdBeta1ResponseOdf]:
    """Helper to create ODFs."""
    if single_shell:
        return [
            mrtrix3tissue.Ss3tCsdBeta1ResponseOdf(response.out_sfwm, bids(param="wm")),
            mrtrix3tissue.Ss3tCsdBeta1ResponseOdf(response.out_gm, bids(param="gm")),
            mrtrix3tissue.Ss3tCsdBeta1ResponseOdf(response.out_csf, bids(param="csf")),
        ]
    return [
        mrtrix.Dwi2fodResponseOdf(response.out_sfwm, bids(param="wm")),
        mrtrix.Dwi2fodResponseOdf(response.out_gm, bids(param="gm")),
        mrtrix.Dwi2fodResponseOdf(response.out_csf, bids(param="csf")),
    ]


def compute_fods(
    input_data: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> mrtrix.MtnormaliseOutputs:
    """Process subject for tractography."""
    logger.info("Computing response function")
    bids = partial(
        utils.io.bids_name,
        datatype="dwi",
        method="dhollander",
        suffix="response",
        ext=".txt",
        **input_group,
    )
    mrconvert = mrtrix.mrconvert(
        input_=input_data["dwi"]["nii"],
        output=input_data["dwi"]["nii"].name.replace(".nii.gz", ".mif"),
        fslgrad=mrtrix.MrconvertFslgrad(
            bvecs=input_data["dwi"]["bvec"],
            bvals=input_data["dwi"]["bval"],
        ),
        nthreads=cfg["opt.threads"],
    )
    dwi2response = mrtrix.dwi2response(
        algorithm=mrtrix.Dwi2responseDhollander(
            input_=mrconvert.output,
            out_sfwm=bids(param="wm"),
            out_gm=bids(param="gm"),
            out_csf=bids(param="csf"),
        ),
        mask=input_data["dwi"]["mask"],
        shells=cfg.get("participant.tractography.shells"),
        lmax=cfg.get("participant.tractography.lmax"),
        nthreads=cfg["opt.threads"],
        config=[
            mrtrix.Dwi2responseConfig(
                "BZeroThreshold", (b0_thresh := str(cfg["participant.b0_thresh"]))
            )
        ],
    )

    logger.info("Computing fiber orientation distribution")
    bids = partial(
        utils.io.bids_name,
        datatype="dwi",
        model="csd",
        suffix="dwimap",
        ext=".mif",
        **input_group,
    )
    if cfg["participant.tractography.single_shell"]:
        response_odf = _create_response_odf(
            response=dwi2response.algorithm,  # type: ignore
            bids=bids,
            single_shell=True,
        )
        if not any(
            isinstance(response, mrtrix3tissue.Ss3tCsdBeta1ResponseOdf)
            for response in response_odf
        ):
            raise TypeError("Response odf is not of type 'Ss3tCsdBeta1ResponseOdf'")
        odfs = mrtrix3tissue.ss3t_csd_beta1(
            dwi=mrconvert.output,
            response_odf=response_odf,  # type: ignore
            mask=input_data["dwi"]["mask"],
            nthreads=cfg["opt.threads"],
            config=[mrtrix3tissue.Ss3tCsdBeta1Config("BZeroThreshold", b0_thresh)],
        )
    else:
        response_odf = _create_response_odf(
            response=dwi2response.algorithm,  # type: ignore
            bids=bids,
            single_shell=False,
        )
        if not any(
            isinstance(response, mrtrix.Dwi2fodResponseOdf) for response in response_odf
        ):
            raise TypeError("Response odf is not of type 'Dwi2fodResponseOdf'")
        odfs = mrtrix.dwi2fod(
            algorithm="msmt_csd",
            dwi=mrconvert.output,
            response_odf=response_odf,  # type: ignore
            mask=input_data["dwi"]["mask"],
            shells=cfg.get("participant.tractography.shells"),
            nthreads=cfg["opt.threads"],
            config=[mrtrix.Dwi2fodConfig("BZeroThreshold", b0_thresh)],
        )

    logger.info("Normalizing fiber orientation distributions")
    normalize_odf = [
        mrtrix.MtnormaliseInputOutput(
            tissue_odf.odf,
            tissue_odf.odf.name.replace("dwimap.mif", "desc-normalized_dwimap.mif"),
        )
        for tissue_odf in odfs.response_odf
    ]
    mtnormalise = mrtrix.mtnormalise(
        input_output=normalize_odf,
        mask=input_data["dwi"]["mask"],
        nthreads=cfg["opt.threads"],
    )

    return mtnormalise


def compute_dti(
    input_data: dict[str, Any],
    input_group: dict[str, Any],
    cfg: dict[str, Any],
    logger: Logger,
    **kwargs,
) -> None:
    """Process diffusion tensors."""
    logger.info("Performing tensor fitting")
    bids = partial(
        utils.io.bids_name,
        datatype="dwi",
        model="tensor",
        suffix="dwimap",
        ext=".nii.gz",
        **input_group,
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
        files=[  # type: ignore
            tensor2metrics.adc,
            tensor2metrics.fa,
            tensor2metrics.ad,
            tensor2metrics.rd,
            tensor2metrics.value,
            tensor2metrics.vector,
        ],
        out_dir=cfg["output_dir"].joinpath(
            utils.io.bids_name(directory=True, datatype="dwi", **input_group)
        ),
    )
