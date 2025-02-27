"""Preprocessing of participants."""

import json
import shutil
from collections import defaultdict
from functools import partial
from logging import Logger
from pathlib import Path
from typing import Any, DefaultDict

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
        input_group = dict(
            zip([key.lstrip("ent__") for key in groupby_keys], group_vals)
        )

        # Outer loops processes the combined directions
        logger.info(f"Processing {(uid := utils.io.bids_name(**input_group))}")

        # Inner loop process per direction, save to list
        dir_outs: DefaultDict[str, list[Any]] = defaultdict(list)
        for idx, (_, row) in enumerate(group.ent.iterrows()):
            input_data = utils.io.get_inputs(b2t=b2t, row=row, cfg=cfg)
            entities = row[["sub", "ses", "run", "dir"]].to_dict()
            bids = partial(utils.io.bids_name, **entities)
            output_fpath = cfg["output_dir"] / bids(datatype="dwi", directory=True)
            dwi = preprocess.denoise.denoise(
                **input_data["dwi"],
                estimator=cfg["participant.preprocess.denoise.estimator"],
                noise_map=cfg["participant.preprocess.denoise.map"],
                extent=cfg.get("participant.preprocess.denoise.extent", None),
                skip=cfg["participant.preprocess.denoise.skip"],
                logger=logger,
                bids=bids,
                output_fpath=output_fpath,
            )

            dwi = preprocess.unring.degibbs(
                dwi=dwi,
                axes=cfg.get("participant.preprocess.unring.axes"),
                nshifts=cfg["participant.preprocess.unring.nshifts"],
                min_w=cfg["participant.preprocess.unring.minW"],
                max_w=cfg["participant.preprocess.unring.maxW"],
                skip=cfg["participant.preprocess.unring.skip"],
                logger=logger,
                bids=bids,
            )

            dir_outs["dwi"].append(dwi or input_data["dwi"]["nii"])
            dir_outs["bval"].append(input_data["dwi"]["bval"])
            dir_outs["bvec"].append(input_data["dwi"]["bvec"])

            if not (
                cfg["participant.preprocess.topup.skip"]
                and cfg["participant.preprocess.eddy.skip"]
            ):
                b0, pe_dir, pe_data = preprocess.dwi.get_phenc_data(
                    dwi=dwi,
                    bval=input_data["dwi"]["bval"],
                    bvec=input_data["dwi"]["bval"],
                    json=input_data["dwi"]["json"],
                    idx=idx,
                    pe_dirs=cfg.get("participant.preprocess.metadata.pe_dirs"),
                    echo_spacing=cfg.get(
                        "participant.preprocess.metadata.echo_spacing"
                    ),
                    bids=bids,
                    logger=logger,
                )

                dir_outs["b0"].append(b0)
                dir_outs["pe_data"].append(pe_data)
                dir_outs["pe_dir"].append(pe_dir)

        bids = partial(utils.io.bids_name, **input_group)
        output_dir = cfg["output_dir"] / bids(datatype="dwi", directory=True)
        match cfg["participant.preprocess.undistort.method"]:
            case "topup":
                if len(set(dir_outs["pe_dir"])) < 2:
                    logger.info("Less than 2 phase-encode directions...skipping topup")
                    cfg["participant.preprocess.topup.skip"] = True

                if not cfg["participant.preprocess.topup.skip"]:
                    logger.info("Running FSL topup")
                    phenc, indices, topup = preprocess.topup.run_apply_topup(
                        **dir_outs,
                        topup_cfg=cfg["participant.preprocess.topup.config"],
                        bids=bids,
                        output_dir=cfg["opt.working_dir"],
                    )
                else:
                    phenc = None
                    indices = None
                    topup = None
                    eddy_mask = None

                if not cfg["participant.preprocess.eddy.skip"]:
                    logger.info("Running FSL's eddy")
                    dwi, bval, bvec = preprocess.eddy.run_eddy(
                        **dir_outs,
                        phenc=phenc,
                        indices=indices,
                        topup=topup,
                        mask=None,
                        slm=cfg.get("participant.preprocess.eddy.slm", None),
                        cnr_maps=cfg["participant.preprocess.eddy.cnr_maps"],
                        repol=cfg["participant.preprocess.eddy.repol"],
                        residuals=cfg["participant.preprocess.eddy.residuals"],
                        shelled=cfg["participant.preprocess.eddy.shelled"],
                        bids=bids,
                        working_dir=cfg["opt.working_dir"],
                        output_dir=output_dir,
                    )
            case "fieldmap":
                # Mimic input_data dict for preprocessing
                if input_data := locals().get("input_data", None):
                    raise ValueError("No input data.")

                fmap_data = {"dwi": {k: v for k, v in input_data["fmap"].items()}}
                entities = BIDSEntities.from_path(fmap_data["dwi"]["nii"]).to_dict()
                entities = {
                    k: v
                    for k, v in entities.items()
                    if k in ["sub", "ses", "run", "dir"]
                }
                bids = partial(utils.io.bids_name, **entities)
                output_fpath = cfg["output_dir"] / bids(datatype="dwi", directory=True)
                fmap = preprocess.denoise.denoise(
                    **fmap_data["dwi"],
                    estimator=cfg["participant.preprocess.denoise.estimator"],
                    noise_map=cfg["participant.preprocess.denoise.map"],
                    extent=cfg.get("participant.preprocess.denoise.extent", None),
                    skip=cfg["participant.preprocess.denoise.skip"],
                    logger=logger,
                    bids=bids,
                    output_fpath=output_fpath,
                )
                fmap = preprocess.unring.degibbs(
                    dwi=fmap,
                    axes=cfg.get("participant.preprocess.unring.axes"),
                    nshifts=cfg["participant.preprocess.unring.nshifts"],
                    min_w=cfg["participant.preprocess.unring.minW"],
                    max_w=cfg["participant.preprocess.unring.maxW"],
                    skip=cfg["participant.preprocess.unring.skip"],
                    logger=logger,
                    bids=bids,
                )

                dir_outs["dwi"].append(fmap)
                dir_outs["bval"].append(fmap_data["dwi"]["bval"])
                dir_outs["bvec"].append(fmap_data["dwi"]["bvec"])

                if not (
                    cfg["participant.preprocess.topup.skip"]
                    and cfg["participant.preprocess.eddy.skip"]
                ):
                    b0, pe_dir, pe_data = preprocess.dwi.get_phenc_data(
                        dwi=fmap,
                        bval=input_data["fmap"]["bval"],
                        bvec=input_data["fmap"]["bval"],
                        json=input_data["fmap"]["json"],
                        idx=len(dir_outs["dwi"]),
                        pe_dirs=cfg.get("participant.preprocess.metadata.pe_dirs"),
                        echo_spacing=cfg.get(
                            "participant.preprocess.metadata.echo_spacing"
                        ),
                        bids=bids,
                        logger=logger,
                    )

                    dir_outs["b0"].append(b0)
                    dir_outs["pe_data"].append(pe_data)
                    dir_outs["pe_dir"].append(pe_dir)

                if len(set(dir_outs["pe_dir"])) < 2:
                    logger.info("Less than 2 phase-encode directions...skipping topup")
                    cfg["participant.preprocess.topup.skip"] = True

                if not cfg["participant.preprocess.topup.skip"]:
                    logger.info("Running FSL topup")
                    phenc, indices, topup = preprocess.topup.run_apply_topup(
                        **dir_outs,
                        topup_cfg=cfg["participant.preprocess.topup.config"],
                        bids=bids,
                        output_dir=cfg["opt.working_dir"],
                    )
                    for key in dir_outs.keys():
                        dir_outs[key].pop()
                else:
                    phenc = None
                    indices = None
                    topup = None
                    eddy_mask = None

                if not cfg["participant.preprocess.eddy.skip"]:
                    logger.info("Running FSL's eddy")
                    dwi, bval, bvec = preprocess.eddy.run_eddy(
                        **dir_outs,
                        phenc=phenc,
                        indices=indices,
                        topup=topup,
                        mask=None,
                        slm=cfg.get("participant.preprocess.eddy.slm", None),
                        cnr_maps=cfg["participant.preprocess.eddy.cnr_maps"],
                        repol=cfg["participant.preprocess.eddy.repol"],
                        residuals=cfg["participant.preprocess.eddy.residuals"],
                        shelled=cfg["participant.preprocess.eddy.shelled"],
                        bids=bids,
                        working_dir=cfg["opt.working_dir"],
                        output_dir=output_dir,
                    )
            case "fugue":
                # For legacy datasets (single phase-encode + fieldmap)
                if input_data := locals().get("input_data", None):
                    raise ValueError("No input data.")

                dwi = None  # type: ignore
                if not cfg["participant.preprocess.eddy.skip"]:
                    logger.info("Running FSL's eddy")
                    dwi, bval, bvec = preprocess.eddy.run_eddy(
                        **dir_outs,
                        phenc=None,
                        indices=None,
                        topup=None,
                        mask=None,
                        slm=cfg.get("participant.preprocess.eddy.slm", None),
                        cnr_maps=cfg["participant.preprocess.eddy.cnr_maps"],
                        repol=cfg["participant.preprocess.eddy.repol"],
                        residuals=cfg["participant.preprocess.eddy.residuals"],
                        shelled=cfg["participant.preprocess.eddy.shelled"],
                        bids=bids,
                        working_dir=cfg["opt.working_dir"],
                        output_dir=output_dir,
                    )

                dwi = preprocess.fugue.run_fugue(
                    dwi=dwi or dir_outs["dwi"][0],
                    fmap=input_data["fmap"]["nii"],
                    pe_dir=dir_outs["pe_dir"][0],
                    json=input_data["dwi"]["json"],
                    echo_spacing=cfg.get(
                        "participant.preprocess.metadata.echo_spacing"
                    ),
                    smooth=cfg["participant.preprocess.fugue.smooth"],
                    logger=logger,
                )
            case "eddymotion":
                if not cfg["participant.preprocess.eddy.skip"]:
                    logger.info("Running eddymotion")
                    dwi, bval, bvec = preprocess.eddymotion.eddymotion(
                        **dir_outs,
                        iters=cfg["participant.preprocess.eddymotion.iters"],
                        seed=cfg["opt.seed_num"],
                        bids=bids,
                        output_dir=cfg["opt.working_dir"],
                        threads=cfg["opt.threads"],
                    )
            case _:
                raise NotImplementedError(
                    "Selected distortion correction method not implemented"
                )

        # Ensure variables are bound
        if input_data := locals().get("input_data", None):
            raise ValueError("No input data.")
        dwi = locals().get("dwi", input_data["dwi"]["nii"])
        bval = locals().get("bval", input_data["dwi"]["bval"])
        bvec = locals().get("bvec", input_data["dwi"]["bvec"])

        logger.info("Performing bias correction")
        dwi, mask = preprocess.biascorrect.biascorrect(
            dwi=dwi,
            bval=bval,
            bvec=bvec,
            spacing=cfg["participant.preprocess.biascorrect.spacing"],
            iters=cfg["partiipant.preproces.biascorrect.iters"],
            shrink=cfg["participant.preprocess.biascorrect.shrink"],
            bids=bids,
            output_dir=cfg["output_dir"] / bids(datatype="dwi", dirctory=True),
        )

        bval_fpath = cfg["output_dir"] / (
            bids(
                datatype="dwi",
                space="T1w",
                res="dwi",
                desc="preproc",
                suffix="dwi",
                ext=".bval",
                return_path=True,
            )
        )
        if not cfg["participant.preprocess.register.skip"]:
            ref_b0, transforms = preprocess.registration.register(
                t1w=input_data["t1w"]["nii"],
                t1w_mask=input_data["dwi"].get("mask"),
                dwi=dwi,
                bval=bval,
                bvec=bvec,
                mask=mask,
                reg_method=cfg["participant.preprocess.register.init"],
                iters=cfg["participant.preprocess.register.iters"],
                metric=cfg["participant.preprocess.register.metric"],
                bids=bids,
                working_dir=cfg["opt.working_dir"],
                output_dir=cfg["output_dir"] / bids(datatype="dwi", directory=True),
                logger=logger,
                threads=cfg["opt.threads"],
            )
            dwi, mask, bvec = preprocess.registration.apply_transform(
                dwi=dwi,
                bvec=bvec,
                ref_b0=ref_b0,
                transforms=transforms,
                t1w_mask=input_data["dwi"].get("mask"),
                mask=input_data["dwi"].get("mask"),
                bids=bids,
                working_dir=cfg["opt.working_dir"],
                output_dir=cfg["output_dir"] / bids(datatype="dwi", directory=True),
                logger=logger,
            )
        else:
            bval_fpath = Path(str(bval_fpath).replace("space-T1w_", ""))
        shutil.copy2(bval, bval_fpath)
        dwi_lib.grad_check(nii=dwi, bvec=bvec, bval=bval_fpath, mask=mask)

        # Create JSON sidecar
        json_fpath = bval_fpath.with_suffix(".json")
        json_fpath.write_text(json.dumps(input_data["dwi"]["json"], indent=2))

        logger.info(f"Completed processing for {uid}")
