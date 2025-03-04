"""Pre-tractography participant processing (to compute FODs)."""

from functools import partial
from logging import Logger
from typing import Any

from bids2table import BIDSTable
from tqdm import tqdm

import nhp_dwiproc.utils as utils
from nhp_dwiproc.lib import dwi as dwi_lib
from nhp_dwiproc.workflow.diffusion import reconst, tractography


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for tractography-level analysis."""
    # Load BIDSTable, querying if necessary
    logger.info("Tractography analysis-level")
    b2t = utils.io.load_b2t(cfg=cfg, logger=logger)
    if cfg.get("participant.query"):
        b2t = b2t.loc[b2t.flat.query(cfg.get("participant.query", "")).index]
    if not isinstance(b2t, BIDSTable):
        raise TypeError(f"Loaded table of type {type(b2t)} instead of BIDSTable")

    dwi_b2t = b2t
    if cfg.get("participant.query_dwi"):
        dwi_b2t = b2t.loc[b2t.flat.query(cfg["participant.query_dwi"]).index]
    if not isinstance(dwi_b2t, BIDSTable):
        raise TypeError(f"Queried table of type {type(dwi_b2t)} instead of BIDSTable")

    # Loop through remaining subjects after query
    groupby_keys = utils.io.valid_groupby(
        b2t=dwi_b2t, keys=["sub", "ses", "run", "space"]
    )
    for group_vals, group in tqdm(
        dwi_b2t.filter_multi(suffix="dwi", ext={"items": [".nii", ".nii.gz"]}).groupby(
            groupby_keys
        )
    ):
        for _, row in group.ent.iterrows():
            input_data = utils.io.get_inputs(b2t=b2t, row=row, cfg=cfg)
            input_group = dict(
                zip([key.lstrip("ent__") for key in groupby_keys], group_vals)
            )

            # Perform processing
            uid = utils.io.bids_name(**input_group)
            logger.info(f"Processing {uid}")
            bids = partial(utils.io.bids_name, datatype="dwi", **input_group)
            output_fpath = cfg["output_dir"] / bids(directory=True)
            dwi_lib.grad_check(**input_data["dwi"])

            logger.info("Performing tensor fitting and generating maps")
            reconst.compute_dti(
                **input_data["dwi"], output_fpath=output_fpath, bids=bids
            )

            logger.info(
                "Computing response function and fibre orientation distribution"
            )
            fods = reconst.compute_fods(
                **input_data["dwi"],
                single_shell=cfg["participant.tractography.single_shell"],
                shells=cfg.get("participant.tractography.shells", None),
                lmax=cfg.get("participant.tractography.lmax", None),
                bids=bids,
            )

            logger.info("Generating tractography and computing weights")
            tractography.generate_tractography(
                dwi_5tt=input_data["dwi"].get("5tt", None),
                method=cfg["participant.tractography.method"],
                fod=fods,
                steps=cfg["participant.tractography.steps"],
                cutoff=cfg["participant.tractography.cutoff"],
                streamlines=cfg["participant.tractography.streamlines"],
                backtrack=cfg["participant.tractography.act.backtrack"],
                nocrop_gmwmi=cfg["participant.tractography.act.nocrop_gmwmi"],
                output_fpath=output_fpath,
                bids=bids,
            )

            logger.info(f"Completed processing for {uid}")
