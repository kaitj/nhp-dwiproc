"""Pre-tractography participant processing (to compute FODs)."""

from logging import Logger
from typing import Any

from bids2table import BIDSTable
from tqdm import tqdm

from nhp_dwiproc.app import utils
from nhp_dwiproc.workflow.diffusion import reconst, tractography


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for tractography-level analysis."""
    logger.info("Tractography analysis-level")
    b2t = utils.io.load_b2t(cfg=cfg, logger=logger)

    # Filter b2t based on string query
    if cfg.get("participant.query"):
        b2t = b2t.loc[b2t.flat.query(cfg.get("participant.query", "")).index]

    assert isinstance(b2t, BIDSTable)
    dwi_b2t = b2t
    if cfg.get("participant.query_dwi"):
        dwi_b2t = b2t.loc[b2t.flat.query(cfg["participant.query_dwi"]).index]

    # Loop through remaining subjects after query
    assert isinstance(dwi_b2t, BIDSTable)
    groupby_keys = utils.io.valid_groupby(b2t=dwi_b2t, keys=["sub", "ses", "run"])
    for group_vals, group in tqdm(
        dwi_b2t.filter_multi(suffix="dwi", ext={"items": [".nii", ".nii.gz"]}).groupby(
            groupby_keys
        )
    ):
        for _, row in group.ent.iterrows():
            input_kwargs: dict[str, Any] = {
                "input_data": utils.io.get_inputs(
                    b2t=b2t,
                    row=row,
                    cfg=cfg,
                ),
                "input_group": dict(
                    zip([key.lstrip("ent__") for key in groupby_keys], group_vals)
                ),
                "cfg": cfg,
                "logger": logger,
            }

            # Perform processing
            logger.info(
                f"Processing {(uid := utils.bids_name(**input_kwargs['input_group']))}"
            )
            wm_mask = reconst.compute_dti(**input_kwargs)
            fods = reconst.compute_fods(**input_kwargs)
            tractography.generate_tractography(
                fod=fods, wm_mask=wm_mask, **input_kwargs
            )
            logger.info(f"Completed processing for {uid}")
