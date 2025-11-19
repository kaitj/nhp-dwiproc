"""Processing of diffusion data to setup tractography."""

import logging
from functools import partial
from pathlib import Path

from niwrap import StyxRuntimeError, mrtrix, mrtrix3tissue
from niwrap_helper import bids_path, save


def _create_response_odf(
    response: mrtrix.Dwi2responseDhollanderOutputs,
    bids: partial,
    single_shell: bool,
    _no_gm: bool = False,
) -> list[
    mrtrix.Dwi2fodResponseOdfParamsDictTagged
    | mrtrix3tissue.Ss3tCsdBeta1ResponseOdfParamsDictTagged
]:
    """Helper to create ODFs."""
    func = (
        mrtrix3tissue.ss3t_csd_beta1_response_odf
        if single_shell
        else mrtrix.dwi2fod_response_odf
    )
    params = [(response.out_sfwm, "wm")]
    if not (single_shell and _no_gm):
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
    bids: partial[str] = partial(bids_path, sub="subject"),
    **kwargs,
) -> mrtrix.MtnormaliseOutputs:
    """Subworkflow for processing fibre orientation distribution maps.

    Args:
        nii: Path to diffusion nifti.
        bvec: Path to diffusion bvec.
        bval: Path to diffusion bval.
        mask: Path to diffusion mask.
        single_shell: Flag to indicate single shell data
        shells: Optionally provide list of shells to process.
        lmax: Optionally provide list of harmonic orders to use for processing.
        bids: Function to generate BIDS filepath.
        **kwargs: Arbitrary keyword arguments

    Raises:
        ValueError: if single-shell data encountered, but flag not used.
    """

    # Helper functons
    def _normalize(
        odfs: mrtrix.Dwi2fodOutputs | mrtrix3tissue.Ss3tCsdBeta1Outputs,
    ) -> list[mrtrix.MtnormaliseInputOutputParamsDictTagged]:
        """Build normalization parameters for ODF outputs."""
        return [
            mrtrix.mtnormalise_input_output(
                odf.odf,
                odf.odf.name.replace("dwimap.mif", "desc-normalized_dwimap.mif"),
            )
            for odf in odfs.response_odf
        ]

    def _run_fod(
        response_odf: list[
            mrtrix.Dwi2fodResponseOdfParamsDictTagged
            | mrtrix3tissue.Ss3tCsdBeta1ResponseOdfParamsDictTagged
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
        fslgrad=mrtrix.mrconvert_fslgrad(bvecs=bvec, bvals=bval),
    )
    dwi2response = mrtrix.dwi2response(
        algorithm=mrtrix.dwi2response_dhollander(
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
            raise ValueError("Single-shell data encountered, but flag not used.")

        # SS3T failed, fallback to SS2T
        logger = kwargs.get("logger", logging.getLogger(__name__))
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
    bids: partial[str] = partial(bids_path, sub="subject"),
    output_fpath: Path = Path.cwd(),
    **kwargs,
) -> None:
    """Sub-workflow to Process diffusion tensors.

    Args:
        nii: Path to diffusion nifti.
        bvec: Path to diffusion bvec.
        bval: Path to diffusion bval.
        mask: Path to diffusion mask.
        bids: Function to generate bids path.
        output_fpath: Output directory to save files to.
        **kwargs: Arbitrary keyword arguments
    """
    dwi2tensor = mrtrix.dwi2tensor(
        dwi=nii,
        dt=bids(ext=".nii.gz"),
        fslgrad=mrtrix.dwi2tensor_fslgrad(bvecs=bvec, bvals=bval),
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
    save(
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
