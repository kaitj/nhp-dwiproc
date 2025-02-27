"""Preprocess steps associated with FSL's topup."""

from functools import partial
from pathlib import Path

import numpy as np
from niwrap import fsl

import nhp_dwiproc.utils as utils
from nhp_dwiproc.workflow.diffusion.preprocess.dwi import gen_topup_inputs


def run_apply_topup(
    b0: list[Path],
    pe_data: list[np.ndarray],
    pe_dir: list[str],
    topup_cfg: Path,
    bids: partial[str] = partial(utils.io.bids_name, sub="subject"),
    output_dir: Path = Path.cwd(),
) -> tuple[Path, list[str], fsl.TopupOutputs]:
    """Perform FSL's topup.

    NOTE: `output_dir` refers to working directory in workflow.
    """
    phenc, b0_norm, indices = gen_topup_inputs(
        b0=b0, pe_data=pe_data, pe_dir=pe_dir, bids=bids, output_dir=output_dir
    )

    topup = fsl.topup(
        imain=b0_norm,
        datain=phenc,
        config=topup_cfg,
        out=f"{bids()}",
        iout=bids(suffix="b0s"),
        fout=bids(suffix="fmap"),
    )
    if not topup.iout:
        raise ValueError("Unable to unwarp b0")

    return phenc, indices, topup
