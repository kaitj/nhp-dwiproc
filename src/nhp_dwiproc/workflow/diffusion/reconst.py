"""Processing of diffusion data to setup tractography."""

import logging
from functools import partial
from pathlib import Path

from niwrap import mrtrix, mrtrix3tissue
from styxdefs import StyxRuntimeError, get_global_runner
from styxgraph import GraphRunner

import nhp_dwiproc.utils as utils


def _create_response_odf(
    response: mrtrix.Dwi2responseDhollanderOutputs,
    bids: partial,
    single_shell: bool,
    _no_gm: bool = False,
) -> list[
    mrtrix.Dwi2fodResponseOdfParameters
    | mrtrix3tissue.Ss3tCsdBeta1ResponseOdfParameters
]:
    """Helper to create ODFs."""
    func = (
        mrtrix3tissue.ss3t_csd_beta1_response_odf_params
        if single_shell
        else mrtrix.dwi2fod_response_odf_params
    )
    params = [(response.out_sfwm, "wm")]
    if not (not single_shell and _no_gm):
        params.append((response.out_gm, "gm"))
    params.append((response.out_csf, "csf"))
    return [func(out, bids(param=param)) for out, param in params]


def compute_fods(
    nii: Path,
    bvec: Path,
    bval: Path,
    mask: Path,
    single_shell: bool,
    shells: list[int | float] | None,
    lmax: list[int] | None,
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
    **kwargs,
) -> mrtrix.MtnormaliseOutputs:
    """Process subject for tractography."""

    # Helper functons
    def _normalize(
        odfs: mrtrix.Dwi2fodOutputs | mrtrix3tissue.Ss3tCsdBeta1Outputs,
    ) -> list[mrtrix.MtnormaliseInputOutputParameters]:
        """Build normalization parameters for ODF outputs."""
        return [
            mrtrix.mtnormalise_input_output_params(
                odf.odf,
                odf.odf.name.replace("dwimap.mif", "desc-normalized_dwimap.mif"),
            )
            for odf in odfs.response_odf
        ]

    def _run_fod(
        response_odf: list[
            mrtrix.Dwi2fodResponseOdfParameters
            | mrtrix3tissue.Ss3tCsdBeta1ResponseOdfParameters
        ],
        single_shell: bool,
    ) -> mrtrix.Dwi2fodOutputs | mrtrix3tissue.Ss3tCsdBeta1Outputs:
        """Estimate FOD depending on shell configuration."""
        if single_shell:
            return mrtrix3tissue.ss3t_csd_beta1(
                dwi=mrconvert.output, response_odf=response_odf, mask=mask
            )
        return mrtrix.dwi2fod(
            algorithm="msmt_csd",
            dwi=mrconvert.output,
            response_odf=response_odf,
            mask=mask,
            shells=shells,
        )

    # Partials
    bids_dwi2response = partial(
        bids, method="dhollander", suffix="response", ext=".txt"
    )
    bids_fod = partial(bids, model="csd", suffix="dwimap", ext=".mif")

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

    try:
        response_odf = _create_response_odf(
            response=dwi2response.algorithm,  # type: ignore
            bids=bids_fod,
            single_shell=single_shell,
        )
        odfs = _run_fod(response_odf, single_shell)
        return mrtrix.mtnormalise(input_output=_normalize(odfs), mask=mask)
    except StyxRuntimeError:
        if not single_shell:
            raise StyxRuntimeError()

        # SS3T failed, fallback to SS2T
        runner = get_global_runner()
        if isinstance(runner, GraphRunner):
            runner = runner.base
        logger = logging.getLogger(runner.logger_name)  # type: ignore
        logger.warning("Unable to perform SS3T, trying SS2T (WM+CSF)")

        response_odf = _create_response_odf(
            response=dwi2response.algorithm,  # type: ignore
            bids=bids_fod,
            single_shell=True,
            _no_gm=True,
        )
        odfs = _run_fod(response_odf, single_shell=False)  # MSMT-CSD w/ WM+CSF
        return mrtrix.mtnormalise(input_output=_normalize(odfs), mask=mask)


def compute_dti(
    nii: Path,
    bvec: Path,
    bval: Path,
    mask: Path,
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
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
