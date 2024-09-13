"""Preprocessing of participants."""

import json
import pathlib as pl
import shutil
from collections import defaultdict
from logging import Logger
from typing import Any

from bids2table import BIDSTable
from tqdm import tqdm

from nhp_dwiproc.app import utils
from nhp_dwiproc.workflow.diffusion import preprocess


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for preprocessing-level analysis."""
    logger.info("Preprocess analysis-level")
    b2t = utils.io.load_b2t(cfg=cfg, logger=logger)

    # Filter b2t based on string query
    if cfg.get("participant.query"):
        b2t = b2t.loc[b2t.flat.query(cfg.get("participant.query")).index]

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
        input_kwargs: dict[str, Any] = {
            "input_group": dict(
                zip([key.lstrip("ent__") for key in groupby_keys], group_vals)
            ),
            "cfg": cfg,
            "logger": logger,
        }
        # Outer loops processes the combined directions
        logger.info(
            f"Processing {(uid := utils.bids_name(**input_kwargs['input_group']))}"
        )

        # Inner loop process per direction, save to list
        dir_outs = defaultdict(list)
        for idx, row in group.ent.iterrows():
            input_kwargs["input_data"] = utils.io.get_inputs(
                b2t=b2t,
                row=row,
                cfg=cfg,
            )
            entities = row[["sub", "ses", "run", "dir"]].to_dict()
            dwi = preprocess.denoise.denoise(entities=entities, **input_kwargs)
            dwi = preprocess.unring.degibbs(dwi=dwi, entities=entities, **input_kwargs)
            b0, pe_dir, pe_data = preprocess.dwi.get_phenc_data(
                dwi=dwi, idx=idx, entities=entities, **input_kwargs
            )

            dir_outs["dwi"].append(dwi or input_kwargs["input_data"]["dwi"]["nii"])
            dir_outs["bval"].append(input_kwargs["input_data"]["dwi"]["bval"])
            dir_outs["bvec"].append(input_kwargs["input_data"]["dwi"]["bvec"])
            dir_outs["b0"].append(b0)
            dir_outs["pe_data"].append(pe_data)
            dir_outs["pe_dir"].append(pe_dir)

        match cfg["participant.preprocess.undistort.method"]:
            case "fsl":
                if len(set(dir_outs["pe_dir"])) < 2:
                    logger.info("Less than 2 phase-encode directions...skipping topup")
                    cfg["participant.preprocess.topup.skip"] = True

                if not cfg["participant.preprocess.topup.skip"]:
                    phenc, indices, topup, eddy_mask = preprocess.topup.run_apply_topup(
                        dir_outs=dir_outs, **input_kwargs
                    )
                else:
                    phenc = None
                    indices = None
                    topup = None
                    eddy_mask = None

                dwi, bval, bvec = preprocess.eddy.run_eddy(
                    phenc=phenc,
                    indices=indices,
                    topup=topup,
                    mask=eddy_mask,
                    dir_outs=dir_outs,
                    **input_kwargs,
                )
            case "eddymotion":
                dwi, bval, bvec = preprocess.eddymotion.eddymotion(
                    dir_outs=dir_outs,
                    **input_kwargs,
                )
            case _:
                raise NotImplementedError(
                    "Selected distortion correction method not implemented"
                )

        dwi, mask = preprocess.biascorrect.biascorrect(
            dwi=dwi, bval=bval, bvec=bvec, **input_kwargs
        )

        bval_fpath = cfg["output_dir"].joinpath(
            utils.bids_name(
                return_path=True,
                datatype="dwi",
                space="T1w",
                res="dwi",
                desc="preproc",
                suffix="dwi",
                ext=".bval",
                **input_kwargs["input_group"],
            )
        )
        if not cfg["participant.preprocess.register.skip"]:
            ref_b0, transforms = preprocess.registration.register(
                dwi=dwi, bval=bval, bvec=bvec, **input_kwargs
            )
            preprocess.registration.apply_transform(
                dwi=dwi,
                bvec=bvec,
                ref_b0=ref_b0,
                transforms=transforms,
                mask=mask,
                **input_kwargs,
            )
        else:
            bval_fpath = pl.Path(str(bval_fpath).replace("space-T1w_", ""))
        shutil.copy2(bval, bval_fpath)

        # Create JSON sidecar
        json_fpath = pl.Path(str(bval_fpath).replace(".bval", ".json"))
        with open(json_fpath, "w") as metadata:
            json.dump(input_kwargs["input_data"]["dwi"]["json"], metadata, indent=2)

        logger.info(f"Completed processing for {uid}")
