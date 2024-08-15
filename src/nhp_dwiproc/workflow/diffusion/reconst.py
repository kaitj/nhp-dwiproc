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
            out_sfwm=bids(
                extra_entities={"method": "dhollander", "param": "wm"},
                suffix="response",
                ext=".txt",
            )
            .to_path()
            .name,
            out_gm=bids(
                extra_entities={"method": "dhollander", "param": "gm"},
                suffix="response",
                ext=".txt",
            )
            .to_path()
            .name,
            out_csf=bids(
                extra_entities={"method": "dhollander", "param": "csf"},
                suffix="response",
                ext=".txt",
            )
            .to_path()
            .name,
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
    response_odf = [
        mrtrix.Dwi2fodResponseOdf(
            dwi2response.algorithm.out_sfwm,
            bids(
                extra_entities={"model": "csd", "param": "wm"},
                suffix="dwimap",
                ext=".mif",
            )
            .to_path()
            .name,
        ),
        mrtrix.Dwi2fodResponseOdf(
            dwi2response.algorithm.out_gm,
            bids(
                extra_entities={"model": "csd", "param": "gm"},
                suffix="dwimap",
                ext=".mif",
            )
            .to_path()
            .name,
        ),
        mrtrix.Dwi2fodResponseOdf(
            dwi2response.algorithm.out_csf,
            bids(
                extra_entities={"model": "csd", "param": "csf"},
                suffix="dwimap",
                ext=".mif",
            )
            .to_path()
            .name,
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
    bids: partial,
    cfg: dict[str, Any],
    logger: Logger,
) -> None:
    """Process diffusion tensors."""
    logger.info("Performing tensor fitting")
    dwi2tensor = mrtrix.dwi2tensor(
        dwi=input_data["dwi"]["nii"],
        dt=bids(extra_entities={"model": "tensor"}, suffix="dwimap", ext=".nii.gz")
        .to_path()
        .name,
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
        adc=bids(
            extra_entities={"model": "tensor", "param": "md"},
            suffix="dwimap",
            ext=".nii.gz",
        )
        .to_path()
        .name,
        fa=bids(
            extra_entities={"model": "tensor", "param": "fa"},
            suffix="dwimap",
            ext=".nii.gz",
        )
        .to_path()
        .name,
        rd=bids(
            extra_entities={"model": "tensor", "param": "rd"},
            suffix="dwimap",
            ext=".nii.gz",
        )
        .to_path()
        .name,
        ad=bids(
            extra_entities={"model": "tensor", "param": "ad"},
            suffix="dwimap",
            ext=".nii.gz",
        )
        .to_path()
        .name,
        value=bids(
            extra_entities={"model": "tensor", "param": "s1"},
            suffix="dwimap",
            ext=".nii.gz",
        )
        .to_path()
        .name,
        vector=bids(
            extra_entities={"model": "tensor", "param": "v1"},
            suffix="dwimap",
            ext=".nii.gz",
        )
        .to_path()
        .name,
        num=[1],
        nthreads=cfg["opt.threads"],
        config=[mrtrix.Tensor2metricConfig("BZeroThreshold", b0_thresh)],
    )

    # Save relevant outputs
    utils.save(
        files=[
            tensor2metrics.adc,
            tensor2metrics.fa,
            tensor2metrics.ad,
            tensor2metrics.rd,
            tensor2metrics.value,
            tensor2metrics.vector,
        ],
        out_dir=cfg["output_dir"].joinpath(bids(datatype="dwi").to_path().parent),
    )
