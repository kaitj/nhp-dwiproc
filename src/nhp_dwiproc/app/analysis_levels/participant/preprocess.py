"""Preprocessing of participants."""

from logging import Logger
from typing import Any

from bids2table import BIDSTable
from tqdm import tqdm

from nhp_dwiproc.app import utils
from nhp_dwiproc.workflow.diffusion.preprocess import denoise, unring


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for preprocessing-level analysis."""
    logger.info("Preprocess analysis-level")
    b2t = utils.io.load_b2t(cfg=cfg, logger=logger)

    # Filter b2t based on string query
    if cfg["participant.query"]:
        b2t = b2t.loc[b2t.flat.query(cfg["participant.query"]).index]

    # Loop through remaining subjects after query
    assert isinstance(b2t, BIDSTable)
    for (subject, session, run_id), group in tqdm(
        b2t.filter_multi(suffix="dwi", ext={"items": [".nii", ".nii.gz"]}).groupby(
            ["ent__sub", "ent__ses", "ent__run"]
        )
    ):
        input_kwargs: dict[str, Any] = {
            "input_group": {"sub": subject, "ses": session, "run": run_id},
            "cfg": cfg,
            "logger": logger,
        }
        # Process per direction in inner loop
        # Outer loops processes the combined directions
        logger.info(
            f"Processing {(uid := utils.bids_name(**input_kwargs['input_group']))}"
        )
        for _, row in group.ent.iterrows():
            input_kwargs["input_data"] = utils.io.get_inputs(b2t=b2t, row=row)
            entities = row[["sub", "ses", "run", "dir"]].to_dict()
            dwi = denoise.denoise(entities=entities, **input_kwargs)
            dwi = unring.degibbs(dwi=dwi, **input_kwargs)

        logger.info(f"Completed processing for {uid}")
