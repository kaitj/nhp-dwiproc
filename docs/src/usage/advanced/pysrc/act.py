#!/usr/bin/env python
"""Script to combine tissue maps into Mrtrix3 compatible 5-tissue type image."""

import itertools
from pathlib import Path
from typing import Any

import nibabel as nib
import nifti
import numpy as np

# Variables
THREADS = 1
DATASET_DIR = Path("/path/to/dataset")
FREESURFER_DIR = Path("/path/to/freesurfer/outputs")
OUTPUT_DIR = Path("/path/to/output")
IMAGE_MAP = Path("/path/to/container/mapping.yaml")

# aparc+aseg segmentations
GM_ASEGS = [
    (8, "Left-Cerebellum_cortex"),
    (47, "Right-Cerebellum_cortex"),
    (17, "Left-Hippocampus"),
    (53, "Right-Hippocampus"),
]
SGM_ASEGS = [
    (18, "Left-Amygdala"),
    (54, "Right-Aymgdala"),
    (10, "Left-Thalamus"),
    (49, "Right-Thalamus"),
    (11, "Left-Caudate"),
    (12, "Left-Putamen"),
    (13, "Left-Pallidum"),
    (26, "Left-Accumbens_area"),
    (50, "Right-Caudate"),
    (51, "Right-Putamen"),
    (52, "Right Pallidum"),
    (58, "Right-Accumbens_area"),
    (27, "Left-substantia_nigra"),
    (59, "Right-substantia_nigra"),
    (28, "Left-ventral_DC"),
    (60, "Right-ventral_DC"),
]
WM_ASEGS = [
    (7, "Left-Cerebellum-WM"),
    (46, "Right-Cerebellum_WM"),
    (250, "Fornix"),
    (192, "Corpus_callosum"),
    (251, "CC_posterior"),
    (252, "CC_mid_posterior"),
    (253, "CC_central"),
    (254, "CC_mid_anterior"),
    (255, "CC_anterior"),
]
CSF_ASEGS = [
    (4, "Left-Lateral_ventricle"),
    (5, "Left-Inferior-lateral_ventricle"),
    (43, "Right-Lateral_ventricle"),
    (44, "Right-Inferior_lateral_ventricle"),
    (14, "3rd_ventricle"),
    (15, "4th_ventricle"),
    (72, "5th_ventricle"),
    (24, "CSF"),
    (31, "Left-Choroid_plexus"),
    (63, "Right-Choroid_plexus"),
]
PATH_ASEGS = [
    (25, "Left-Lesion"),
    (57, "Right-Lesion"),
]
BRAIN_STEM_ASEG = [(16, "Brainstem")]


def load_nifti(fpath: str | Path) -> nib.Nifti1Image:
    """Helper to load nifti image quickly."""
    hdr, img = nifti.read_volume(str(fpath))
    new_hdr = nib.Nifti1Header()
    for k, v in hdr.items():
        if k in new_hdr:
            new_hdr[k] = v
    aff = new_hdr.get_best_affine()
    return nib.Nifti1Image(dataobj=img, affine=aff, header=new_hdr)


def process_map(
    tmap: nib.Nifti1Image,
    aseg: nib.Nifti1Image,
    mask: nib.Nifti1Image,
    include: list[list[tuple[int, str]]],
    exclude: list[list[tuple[int, str]]],
) -> np.ndarray:
    """Generate tissue maps."""
    # Load in GM tissue and use as a base for tissue map
    out_img = tmap.dataobj.astype(int)
    out_img[out_img > 0] = 1
    # Handle segmentations
    for aseg_label, aseg_name in itertools.chain(*include):
        out_img[aseg.dataobj == aseg_label] = 1
    for aseg_label, aseg_name in itertools.chain(*exclude):
        out_img[aseg.dataobj == aseg_label] = 0
    # Apply mask
    out_img = out_img - mask.dataobj
    return out_img


if __name__ == "__main__":
    # Participant metadata
    participant = "001"
    session = "AA"
    run = 1

    # Process data
    fs_dir = FREESURFER_DIR / participant
    gm = load_nifti(fs_dir / "GM.nii.gz")
    wm = load_nifti(fs_dir / "WM.nii.gz")
    csf = load_nifti(fs_dir / "CSF.nii.gz")
    mask = load_nifti(fs_dir / "brain_mask.nii.gz")
    aseg = load_nifti(fs_dir / "aparc+aseg.nii.gz")

    # Process maps
    map_cfgs: list[dict[str, Any]] = [
        {
            "tmap": gm,
            "include": [GM_ASEGS],
            "exclude": [
                SGM_ASEGS,
                WM_ASEGS,
                CSF_ASEGS,
                PATH_ASEGS,
                BRAIN_STEM_ASEG,
            ],
        },
        {
            "tmap": nib.Nifti1Image(dataobj=np.zeros(gm.shape), affine=gm.affine),
            "include": [SGM_ASEGS],
            "exclude": [GM_ASEGS, WM_ASEGS, CSF_ASEGS, PATH_ASEGS, BRAIN_STEM_ASEG],
        },
        {
            "tmap": wm,
            "include": [WM_ASEGS],
            "exclude": [
                GM_ASEGS,
                SGM_ASEGS,
                CSF_ASEGS,
                PATH_ASEGS,
                BRAIN_STEM_ASEG,
            ],
        },
        {
            "tmap": csf,
            "include": [CSF_ASEGS],
            "exclude": [GM_ASEGS, SGM_ASEGS, WM_ASEGS, PATH_ASEGS, BRAIN_STEM_ASEG],
        },
        {
            "tmap": nib.Nifti1Image(dataobj=np.zeros(gm.shape), affine=gm.affine),
            "include": [PATH_ASEGS],
            "exclude": [SGM_ASEGS, WM_ASEGS, CSF_ASEGS, BRAIN_STEM_ASEG],
        },
    ]
    tmaps = [
        process_map(
            tmap=cfg["tmap"],
            aseg=aseg,
            mask=mask,
            include=cfg["include"],
            exclude=cfg["exclude"],
        )
        for cfg in map_cfgs
    ]

    # Create 5tt image from tmaps
    tt_map = np.stack(tmaps, axis=3)
    tt_img = nib.Nifti1Image(dataobj=tt_map, affine=gm.affine)
    tt_fpath = (
        f"sub-{participant}/"
        f"ses-{session}/"
        "anat/"
        f"sub-{participant}_ses-{session}_run-{run}_res-orig_method-aseg_desc-5tt_dseg.nii.gz"
    )
    out_fpath = OUTPUT_DIR / tt_fpath
    out_fpath.mkdir(parents=True, exist_ok=True)
    nib.save(tt_img, out_fpath)
