"""Processing of diffusion data to setup tractography."""

from functools import partial
from pathlib import Path

import niwrap_helper
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
    nii: Path,
    bvec: Path,
    bval: Path,
    mask: Path,
    single_shell: bool,
    shells: list[int | float] | None,
    lmax: list[int] | None,
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    **kwargs,
) -> mrtrix.MtnormaliseOutputs:
    """Process subject for tractography."""
    bids_dwi2response = partial(
        bids, method="dhollander", suffix="response", ext=".txt"
    )
    mrconvert = mrtrix.mrconvert(
        input_=nii,
        output=nii.name.replace(".nii.gz", ".mif"),
        fslgrad=mrtrix.mrconvert_fslgrad_params(bvecs=bvec, bvals=bval),
    )
    dwi2response = mrtrix.dwi2response(
        algorithm=mrtrix.dwi2response_dhollander_params(
            input_=mrconvert.output,
            out_sfwm=bids_dwi2response(param="wm"),
            out_gm=bids_dwi2response(param="gm"),
            out_csf=bids_dwi2response(param="csf"),
        ),
        mask=mask,
        shells=shells,  # type: ignore
        lmax=lmax,
    )
    bids_fod = partial(bids, model="csd", suffix="dwimap", ext=".mif")
    if single_shell:
        response_odf = _create_response_odf(
            response=dwi2response.algorithm,  # type: ignore
            bids=bids_fod,
            single_shell=True,
        )
        odfs = mrtrix3tissue.ss3t_csd_beta1(
            dwi=mrconvert.output, response_odf=response_odf, mask=mask
        )
    else:
        response_odf = _create_response_odf(
            response=dwi2response.algorithm,  # type: ignore
            bids=bids_fod,
            single_shell=False,
        )
        odfs = mrtrix.dwi2fod(
            algorithm="msmt_csd",
            dwi=mrconvert.output,
            response_odf=response_odf,
            mask=mask,
            shells=shells,
        )

    normalize_odf = [
        mrtrix.mtnormalise_input_output_params(
            tissue_odf.odf,
            tissue_odf.odf.name.replace("dwimap.mif", "desc-normalized_dwimap.mif"),
        )
        for tissue_odf in odfs.response_odf
    ]
    return mrtrix.mtnormalise(input_output=normalize_odf, mask=mask)


def compute_dti(
    nii: Path,
    bvec: Path,
    bval: Path,
    mask: Path,
    bids: partial[str] = partial(niwrap_helper.bids_path, sub="subject"),
    output_fpath: Path = Path.cwd(),
    **kwargs,
) -> None:
    """Process diffusion tensors."""
    dwi2tensor = mrtrix.dwi2tensor(
        dwi=nii,
        dt=bids(ext=".nii.gz"),
        fslgrad=mrtrix.dwi2tensor_fslgrad_params(bvecs=bvec, bvals=bval),
        mask=mask,
    )
    tensor2metrics = mrtrix.tensor2metric(
        tensor=dwi2tensor.dt,
        mask=mask,
        adc=bids(param="MD", suffix="dwimap", ext=".nii.gz"),
        fa=bids(param="FA", suffix="dwimap", ext=".nii.gz"),
        rd=bids(param="RD", suffix="dwimap", ext=".nii.gz"),
        ad=bids(param="AD", suffix="dwimap", ext=".nii.gz"),
        value=bids(param="S1", suffix="dwimap", ext=".nii.gz"),
        vector=bids(param="V1", suffix="dwimap", ext=".nii.gz"),
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
        out_dir=output_fpath,
    )
