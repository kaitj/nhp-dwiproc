"""Preprocess steps associated with FSL's topup."""

import logging
from functools import partial
from pathlib import Path

import numpy as np
from niwrap import fsl
from niwrap_helper.bids import StrPath, bids_path

from nhp_dwiproc.app.workflow.preprocess.dwi import gen_topup_inputs
from nhp_dwiproc.config.preprocess import TopupConfig


def run_apply_topup(
    b0: list[Path],
    pe_data: list[np.ndarray],
    pe_dir: list[str],
    topup_opts: TopupConfig | None = TopupConfig(),
    bids: partial = partial(bids_path, sub="subject"),
    output_dir: StrPath = Path.cwd(),
    **kwargs,
) -> tuple[Path | None, list[str] | None, fsl.TopupOutputs | None]:
    """Perform FSL's topup.

    Args:
        b0: List of b0s to process.
        pe_data: List of phase-encoding data files.
        pe_dir: List of phase-encoding directions.
        topup_opts: Topup configuration options.
        bids: Function to generate BIDS filename.
        output_dir: Working directory to generate output files to.
        **kwargs: Arbitrary keyword arguments.

    Returns:
        A 3-tuple with the phase encode lines, the associated indices, and topup
        outputs.

    Raises:
        TypeError: If unexpected configuration type.
        ValueError: If unable to unwrap b0.
    """
    if not isinstance(topup_opts, TopupConfig):
        raise TypeError(f"Expected TopupConfig, got {type(topup_opts)}")
    logger = kwargs.get("logger", logging.Logger(__name__))

    if len(set(pe_dir)) < 2:
        logger.info("Less than 2 phase-encode directions...skipping topup")
        topup_opts.skip = True

    if not topup_opts.skip:
        phenc, b0_norm, indices = gen_topup_inputs(
            b0=b0,
            pe_data=pe_data,
            pe_dir=pe_dir,
            bids=bids,
            output_dir=Path(output_dir),
        )
        topup = fsl.topup(
            imain=b0_norm,
            datain=phenc,
            config=topup_opts.config,
            out=f"{bids()}",
            iout=bids(suffix="b0s"),
            fout=bids(suffix="fmap"),
        )
        if not topup.iout:
            raise ValueError("Unable to unwarp b0")
        return phenc, indices, topup
    else:
        return None, None, None
