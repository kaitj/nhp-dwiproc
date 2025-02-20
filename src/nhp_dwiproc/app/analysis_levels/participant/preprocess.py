"""Preprocessing of participants."""

import json
import pathlib as pl
import shutil
from collections import defaultdict
from logging import Logger
from typing import Any

from bids2table import BIDSEntities, BIDSTable
from tqdm import tqdm

import nhp_dwiproc.utils as utils
from nhp_dwiproc.lib import dwi as dwi_lib
from nhp_dwiproc.workflow.diffusion import preprocess


def run(cfg: dict[str, Any], logger: Logger) -> None:
    """Runner for preprocessing-level analysis."""
    logger.info("Preprocess analysis-level")
    b2t = utils.io.load_b2t(cfg=cfg, logger=logger)

    # Filter b2t based on string query
    if cfg.get("participant.query"):
        b2t = b2t.loc[b2t.flat.query(cfg["participant.query"]).index]
    if not isinstance(b2t, BIDSTable):
        raise TypeError(f"Expected BIDSTable, but got {type(b2t).__name__}")

    dwi_b2t = b2t
    if cfg.get("participant.query_dwi"):
        dwi_b2t = b2t.loc[b2t.flat.query(cfg["participant.query_dwi"]).index]
    if not isinstance(dwi_b2t, BIDSTable):
        raise TypeError(f"Expected BIDSTable, but got {type(dwi_b2t).__name__}")

    # Loop through remaining subjects after query
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
            f"Processing {(uid := utils.io.bids_name(**input_kwargs['input_group']))}"
        )

        # Inner loop process per direction, save to list
        dir_outs = defaultdict(list)
        for idx, (_, row) in enumerate(group.ent.iterrows()):
            input_kwargs["input_data"] = utils.io.get_inputs(
                b2t=b2t,
                row=row,
                cfg=cfg,
            )
            entities = row[["sub", "ses", "run", "dir"]].to_dict()
            dwi = preprocess.denoise.denoise(entities=entities, **input_kwargs)
            dwi = preprocess.unring.degibbs(dwi=dwi, entities=entities, **input_kwargs)

            dir_outs["dwi"].append(dwi or input_kwargs["input_data"]["dwi"]["nii"])
            dir_outs["bval"].append(input_kwargs["input_data"]["dwi"]["bval"])
            dir_outs["bvec"].append(input_kwargs["input_data"]["dwi"]["bvec"])

            if not (
                cfg["participant.preprocess.topup.skip"]
                and cfg["participant.preprocess.eddy.skip"]
            ):
                b0, pe_dir, pe_data = preprocess.dwi.get_phenc_data(
                    dwi=dwi,
                    idx=idx,
                    entities=entities,
                    input_data=input_kwargs["input_data"],
                    cfg=cfg,
                    logger=logger,
                )
                dir_outs["b0"].append(b0)
                dir_outs["pe_data"].append(pe_data)
                dir_outs["pe_dir"].append(pe_dir)

        match cfg["participant.preprocess.undistort.method"]:
            case "topup":
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

                if not cfg["participant.preprocess.eddy.skip"]:
                    dwi, bval, bvec = preprocess.eddy.run_eddy(
                        phenc=phenc,
                        indices=indices,
                        topup=topup,
                        mask=eddy_mask,
                        dir_outs=dir_outs,
                        **input_kwargs,
                    )
            case "fieldmap":
                # Mimic input_data dict for preprocessing
                fmap_data = {
                    "dwi": {
                        "nii": input_kwargs["input_data"]["fmap"]["nii"],
                        "bval": input_kwargs["input_data"]["fmap"]["bval"],
                        "bvec": input_kwargs["input_data"]["fmap"]["bvec"],
                        "json": input_kwargs["input_data"]["fmap"]["json"],
                    }
                }
                entities = BIDSEntities.from_path(fmap_data["dwi"]["nii"]).to_dict()
                entities = {
                    k: v
                    for k, v in entities.items()
                    if k in ["sub", "ses", "run", "dir"]
                }
                fmap = preprocess.denoise.denoise(
                    entities=entities,
                    input_data=fmap_data,
                    cfg=cfg,
                    logger=logger,
                )
                fmap = preprocess.unring.degibbs(
                    dwi=fmap, entities=entities, cfg=cfg, logger=logger
                )
                fmap = locals().get("fmap", fmap_data["dwi"]["nii"])
                dir_outs["dwi"].append(fmap)
                dir_outs["bval"].append(fmap_data["dwi"]["bval"])
                dir_outs["bvec"].append(fmap_data["dwi"]["bvec"])

                if not (
                    cfg["participant.preprocess.topup.skip"]
                    and cfg["participant.preprocess.eddy.skip"]
                ):
                    b0, pe_dir, pe_data = preprocess.dwi.get_phenc_data(
                        dwi=fmap,
                        idx=len(dir_outs["dwi"]),
                        entities=entities,
                        input_data=fmap_data,
                        cfg=cfg,
                        logger=logger,
                    )
                    dir_outs["b0"].append(b0)
                    dir_outs["pe_data"].append(pe_data)
                    dir_outs["pe_dir"].append(pe_dir)

                if len(set(dir_outs["pe_dir"])) < 2:
                    logger.info("Less than 2 phase-encode directions...skipping topup")
                    cfg["participant.preprocess.topup.skip"] = True

                if not cfg["participant.preprocess.topup.skip"]:
                    phenc, indices, topup, eddy_mask = preprocess.topup.run_apply_topup(
                        dir_outs=dir_outs, **input_kwargs
                    )
                    for key in dir_outs.keys():
                        dir_outs[key].pop()
                else:
                    phenc = None
                    indices = None
                    topup = None
                    eddy_mask = None

                if not cfg["participant.preprocess.eddy.skip"]:
                    dwi, bval, bvec = preprocess.eddy.run_eddy(
                        phenc=phenc,
                        indices=indices,
                        topup=topup,
                        mask=eddy_mask,
                        dir_outs=dir_outs,
                        **input_kwargs,
                    )
            case "fugue":
                # For legacy datasets (single phase-encode + fieldmap)
                dwi = None
                if not cfg["participant.preprocess.eddy.skip"]:
                    dwi, bval, bvec = preprocess.eddy.run_eddy(
                        phenc=None,
                        indices=None,
                        topup=None,
                        mask=None,
                        dir_outs=dir_outs,
                        **input_kwargs,
                    )

                dwi = preprocess.fugue.run_fugue(
                    dwi=dwi or dir_outs["dwi"][0],
                    pe_dir=dir_outs["pe_dir"][0],
                    dir_outs=dir_outs,
                    **input_kwargs,
                )
            case "eddymotion":
                if not cfg["participant.preprocess.eddy.skip"]:
                    dwi, bval, bvec = preprocess.eddymotion.eddymotion(
                        dir_outs=dir_outs,
                        **input_kwargs,
                    )
            case _:
                raise NotImplementedError(
                    "Selected distortion correction method not implemented"
                )

        # Ensure variables are bound
        dwi = locals().get("dwi", input_kwargs["input_data"]["dwi"]["nii"])
        bval = locals().get("bval", input_kwargs["input_data"]["dwi"]["bval"])
        bvec = locals().get("bvec", input_kwargs["input_data"]["dwi"]["bvec"])
        dwi, mask = preprocess.biascorrect.biascorrect(
            dwi=dwi,
            bval=bval,
            bvec=bvec,
            **input_kwargs,
        )

        bval_fpath = cfg["output_dir"] / (
            utils.io.bids_name(
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
                dwi=dwi, bval=bval, bvec=bvec, mask=mask, **input_kwargs
            )
            dwi, mask, bvec = preprocess.registration.apply_transform(
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
        dwi_lib.grad_check(nii=dwi, bvec=bvec, bval=bval_fpath, mask=mask, cfg=cfg)

        # Create JSON sidecar
        json_fpath = bval_fpath.with_suffix(".json")
        json_fpath.write_text(
            json.dumps(input_kwargs["input_data"]["dwi"]["json"], indent=2)
        )

        logger.info(f"Completed processing for {uid}")
