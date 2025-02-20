"""Processing of diffusion data to setup tractography."""

from functools import partial
from logging import Logger
from typing import Any

from niwrap import mrtrix, mrtrix3tissue

import nhp_dwiproc.utils as utils


def _create_response_odf(
    response: mrtrix.Dwi2responseDhollanderOutputs, bids: partial, single_shell: bool
) -> list[
    mrtrix.Dwi2fodResponseOdfParameters
    | mrtrix3tissue.Ss3tCsdBeta1ResponseOdfParameters
]:
    """Helper to create ODFs."""
    if single_shell:
        return [
            mrtrix3tissue.ss3t_csd_beta1_response_odf_params(
                response.out_sfwm, bids(param="wm")
            ),
            mrtrix3tissue.ss3t_csd_beta1_response_odf_params(
                response.out_gm, bids(param="gm")
            ),
            mrtrix3tissue.ss3t_csd_beta1_response_odf_params(
                response.out_csf, bids(param="csf")
            ),
        ]
    return [
        mrtrix.dwi2fod_response_odf_params(response.out_sfwm, bids(param="wm")),
        mrtrix.dwi2fod_response_odf_params(response.out_gm, bids(param="gm")),
        mrtrix.dwi2fod_response_odf_params(response.out_csf, bids(param="csf")),
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
        fslgrad=mrtrix.mrconvert_fslgrad_params(
            bvecs=input_data["dwi"]["bvec"], bvals=input_data["dwi"]["bval"]
        ),
    )
    dwi2response = mrtrix.dwi2response(
        algorithm=mrtrix.dwi2response_dhollander_params(
            input_=mrconvert.output,
            out_sfwm=bids(param="wm"),
            out_gm=bids(param="gm"),
            out_csf=bids(param="csf"),
        ),
        mask=input_data["dwi"]["mask"],
        shells=cfg.get("participant.tractography.shells"),
        lmax=cfg.get("participant.tractography.lmax"),
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
            isinstance(response, mrtrix3tissue.Ss3tCsdBeta1ResponseOdfOutputs)
            for response in response_odf
        ):
            raise TypeError("Response odf is not of type 'Ss3tCsdBeta1ResponseOdf'")
        odfs = mrtrix3tissue.ss3t_csd_beta1(
            dwi=mrconvert.output,
            response_odf=response_odf,
            mask=input_data["dwi"]["mask"],
        )
    else:
        response_odf = _create_response_odf(
            response=dwi2response.algorithm,  # type: ignore
            bids=bids,
            single_shell=False,
        )
        if not any(
            isinstance(response, mrtrix.Dwi2fodResponseOdfOutputs)
            for response in response_odf
        ):
            raise TypeError("Response odf is not of type 'Dwi2fodResponseOdf'")
        odfs = mrtrix.dwi2fod(
            algorithm="msmt_csd",
            dwi=mrconvert.output,
            response_odf=response_odf,
            mask=input_data["dwi"]["mask"],
            shells=cfg.get("participant.tractography.shells"),
        )

    logger.info("Normalizing fiber orientation distributions")
    normalize_odf = [
        mrtrix.mtnormalise_input_output_params(
            tissue_odf.odf,
            tissue_odf.odf.name.replace("dwimap.mif", "desc-normalized_dwimap.mif"),
        )
        for tissue_odf in odfs.response_odf
    ]
    mtnormalise = mrtrix.mtnormalise(
        input_output=normalize_odf, mask=input_data["dwi"]["mask"]
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
        fslgrad=mrtrix.dwi2tensor_fslgrad_params(
            bvecs=input_data["dwi"]["bvec"], bvals=input_data["dwi"]["bval"]
        ),
        mask=input_data["dwi"]["mask"],
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
        out_dir=cfg["output_dir"]
        / (utils.io.bids_name(directory=True, datatype="dwi", **input_group)),
    )
