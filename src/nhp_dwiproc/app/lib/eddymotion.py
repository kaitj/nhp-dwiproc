"""Helper functions adapted from eddymotion to perform correction.

Original: https://github.com/nipreps/eddymotion/
Copyright 2022 The NiPreps Developers <nipreps@gmail.com>
Licensed under Apache License, Version 2.0
"""

from collections import namedtuple
from dataclasses import dataclass, field, fields
from pathlib import Path
from tempfile import TemporaryDirectory, mkstemp
from typing import Any
from uuid import uuid4

import h5py
import nibabel as nb
import numpy as np
from nitransforms.io.itk import ITKLinearTransform
from nitransforms.linear import Affine
from niwrap import ants
from scipy import ndimage

# --------------------------------------------------------------------------- #
#  Registration stage configuration (adapted from eddymotion config JSONs)
# --------------------------------------------------------------------------- #


def _build_stages(
    reg_target_type: str,
    i_iter: int,
    fixed: Path,
    moving: Path,
) -> list[ants.AntsRegistrationStageParamsDict]:
    """Build niwrap stage dicts for ANTs registration.

    Parameters
    ----------
    reg_target_type : str
        Either ``"b0"`` or ``"dwi"``.
    i_iter : int
        Registration iteration index (0 or 1).
    fixed : Path
        Fixed (reference) image path.
    moving : Path
        Moving image path.

    Returns:
    -------
    list[dict]
        List of stage dicts for ``ants.ants_registration``.
    """
    if reg_target_type == "b0":
        # From eddymotion config/dwi-to-b0_level0.json
        # Two Rigid stages with Mattes metric
        sampling_reg = ants.ants_registration_sampling_strategy_1(
            sampling_strategy_value="Regular",
            sampling_percentage=ants.ants_registration_sampling_percentage_1(
                sampling_percentage_value=0.2,
            ),
        )
        sampling_rand = ants.ants_registration_sampling_strategy_1(
            sampling_strategy_value="Random",
            sampling_percentage=ants.ants_registration_sampling_percentage_1(
                sampling_percentage_value=0.1,
            ),
        )
        return [
            {
                "transform": ants.ants_registration_transform_rigid(
                    gradient_step=0.01,
                ),
                "metric": ants.ants_registration_metric_mattes(
                    fixed_image=str(fixed),
                    moving_image=str(moving),
                    metric_weight=1.0,
                    number_of_bins=ants.ants_registration_number_of_bins_1(
                        number_of_bins_value=32,
                        sampling_strategy=sampling_reg,
                    ),
                ),
                "convergence": ants.ants_registration_convergence(
                    convergence="[100,50],[25]",
                    convergence_threshold=1e-5,
                    convergence_window_size=10,
                ),
                "smoothing_sigmas": "[2.0,0.0],[0.0]",
                "shrink_factors": "[2,1],[1]",
                "use_histogram_matching": True,
            },
            {
                "transform": ants.ants_registration_transform_rigid(
                    gradient_step=0.001,
                ),
                "metric": ants.ants_registration_metric_mattes(
                    fixed_image=str(fixed),
                    moving_image=str(moving),
                    metric_weight=1.0,
                    number_of_bins=ants.ants_registration_number_of_bins_1(
                        number_of_bins_value=32,
                        sampling_strategy=sampling_rand,
                    ),
                ),
                "convergence": ants.ants_registration_convergence(
                    convergence="[25]",
                    convergence_threshold=1e-6,
                    convergence_window_size=2,
                ),
                "smoothing_sigmas": "[0.0]",
                "shrink_factors": "[1]",
                "use_histogram_matching": True,
            },
        ]

    # reg_target_type == "dwi"
    if i_iter == 0:
        # From eddymotion config/dwi-to-dwi_level0.json
        # Two Rigid stages: Mattes + GlobalCorrelation
        sampling_reg_0 = ants.ants_registration_sampling_strategy_1(
            sampling_strategy_value="Random",
            sampling_percentage=ants.ants_registration_sampling_percentage_1(
                sampling_percentage_value=0.2,
            ),
        )
        ants.ants_registration_sampling_strategy_1(
            sampling_strategy_value="Random",
            sampling_percentage=ants.ants_registration_sampling_percentage_1(
                sampling_percentage_value=0.1,
            ),
        )
        return [
            {
                "transform": ants.ants_registration_transform_rigid(
                    gradient_step=0.01,
                ),
                "metric": ants.ants_registration_metric_mattes(
                    fixed_image=str(fixed),
                    moving_image=str(moving),
                    metric_weight=1.0,
                    number_of_bins=ants.ants_registration_number_of_bins_1(
                        number_of_bins_value=32,
                        sampling_strategy=sampling_reg_0,
                    ),
                ),
                "convergence": ants.ants_registration_convergence(
                    convergence="[100]",
                    convergence_threshold=1e-6,
                    convergence_window_size=15,
                ),
                "smoothing_sigmas": "[2.0]",
                "shrink_factors": "[1]",
                "use_histogram_matching": True,
            },
            {
                "transform": ants.ants_registration_transform_rigid(
                    gradient_step=0.001,
                ),
                "metric": ants.ants_registration_metric_global_correlation(
                    fixed_image=str(fixed),
                    moving_image=str(moving),
                    metric_weight=1.0,
                    radius=ants.ants_registration_radius_1(
                        radius_value=5,
                        sampling_strategy=ants.ants_registration_sampling_strategy_2(
                            sampling_strategy_value="Random",
                            sampling_percentage=ants.ants_registration_sampling_percentage_2(
                                sampling_percentage_value=0.1,
                            ),
                        ),
                    ),
                ),
                "convergence": ants.ants_registration_convergence(
                    convergence="[20]",
                    convergence_threshold=1e-7,
                    convergence_window_size=5,
                ),
                "smoothing_sigmas": "[0.0]",
                "shrink_factors": "[1]",
                "use_histogram_matching": True,
            },
        ]

    # i_iter == 1
    # From eddymotion config/dwi-to-dwi_level1.json
    # Two Affine stages: Mattes + GlobalCorrelation
    sampling_reg_1 = ants.ants_registration_sampling_strategy_1(
        sampling_strategy_value="Regular",
        sampling_percentage=ants.ants_registration_sampling_percentage_1(
            sampling_percentage_value=0.2,
        ),
    )
    ants.ants_registration_sampling_strategy_1(
        sampling_strategy_value="Random",
        sampling_percentage=ants.ants_registration_sampling_percentage_1(
            sampling_percentage_value=0.1,
        ),
    )
    return [
        {
            "transform": ants.ants_registration_transform_affine(
                gradient_step=0.01,
            ),
            "metric": ants.ants_registration_metric_mattes(
                fixed_image=str(fixed),
                moving_image=str(moving),
                metric_weight=1.0,
                number_of_bins=ants.ants_registration_number_of_bins_1(
                    number_of_bins_value=32,
                    sampling_strategy=sampling_reg_1,
                ),
            ),
            "convergence": ants.ants_registration_convergence(
                convergence="[100]",
                convergence_threshold=1e-6,
                convergence_window_size=15,
            ),
            "smoothing_sigmas": "[2.0]",
            "shrink_factors": "[1]",
            "use_histogram_matching": True,
        },
        {
            "transform": ants.ants_registration_transform_affine(
                gradient_step=0.001,
            ),
            "metric": ants.ants_registration_metric_global_correlation(
                fixed_image=str(fixed),
                moving_image=str(moving),
                metric_weight=1.0,
                radius=ants.ants_registration_radius_1(
                    radius_value=5,
                    sampling_strategy=ants.ants_registration_sampling_strategy_2(
                        sampling_strategy_value="Random",
                        sampling_percentage=ants.ants_registration_sampling_percentage_2(
                            sampling_percentage_value=0.1,
                        ),
                    ),
                ),
            ),
            "convergence": ants.ants_registration_convergence(
                convergence="[50]",
                convergence_threshold=1e-7,
                convergence_window_size=5,
            ),
            "smoothing_sigmas": "[0.0]",
            "shrink_factors": "[1]",
            "use_histogram_matching": True,
        },
    ]


# --------------------------------------------------------------------------- #
#  DWI data class
# --------------------------------------------------------------------------- #


def _data_repr(value: np.ndarray | None) -> str:
    if value is None:
        return "None"
    return f"<{'x'.join(str(v) for v in value.shape)} ({value.dtype})>"


@dataclass(slots=True, kw_only=True)
class DWI:
    """Data representation structure for dMRI data."""

    dataobj: np.ndarray | None = field(default=None)
    """A numpy ndarray object for the data array, without *b=0* volumes."""
    affine: np.ndarray | None = field(default=None)
    """Best affine for RAS-to-voxel conversion of coordinates (NIfTI header)."""
    brainmask: np.ndarray | None = field(default=None)
    """A boolean ndarray object containing a corresponding brainmask."""
    bzero: np.ndarray | None = field(default=None)
    """A *b=0* reference map, preferably obtained by some smart averaging."""
    gradients: np.ndarray | None = field(default=None)
    """A 2D numpy array of the gradient table in RAS+B format."""
    em_affines: np.ndarray | None = field(default=None)
    """List of affine matrices that bring DWIs into alignment."""
    fieldmap: np.ndarray | None = field(default=None)
    """A 3D displacements field to unwarp susceptibility distortions."""
    _filepath: Path | None = field(default=None, repr=False)
    """HDF5 file path, or parent directory when set externally."""

    def __repr__(self) -> str:
        """Print fields with asssociated values in DWI object."""
        parts = []
        for fld in fields(self):
            if fld.name.startswith("_"):
                continue
            value = getattr(self, fld.name)
            parts.append(f"{fld.name}={_data_repr(value)}")
        return f"DWI({', '.join(parts)})"

    def get_filename(self) -> Path:
        """Return the path for the internal HDF5 file.

        If ``_filepath`` is ``None``, creates a fresh temp file in the
        system temp directory. If it refers to a directory, generates
        a unique filename under that directory and caches the result.
        Otherwise returns the already-cached path.
        """
        if self._filepath is None:
            self._filepath = Path(mkstemp(suffix=".h5")[1])
        elif self._filepath.is_dir():
            self._filepath = self._filepath / f"{uuid4().hex}.h5"
        return self._filepath

    def __len__(self) -> int:
        """Obtain the number of high-*b* orientations."""
        if self.dataobj is None:
            raise ValueError("Expected an np.ndarray, but got None")
        return self.dataobj.shape[-1]  # type: ignore[union-attr]

    def set_transform(self, index: int, affine: np.ndarray, order: int = 3) -> None:
        """Set an affine, and update data object and gradients."""
        if self.dataobj is None:
            raise ValueError("Expected an np.ndarray, but got None")
        reference = namedtuple(
            "ImageGrid", ("shape", "affine")
        )(  # type: ignore[call-arg]
            shape=self.dataobj.shape[:3], affine=self.affine
        )

        xform = Affine(matrix=affine, reference=reference)

        h5path = self.get_filename()
        if not h5path.exists():
            self.to_filename(h5path)

        with h5py.File(h5path, "r") as in_file:
            root = in_file["/0"]
            dwframe = np.asanyarray(root["dataobj"][..., index])
            bvec = np.asanyarray(root["gradients"][:3, index])

        dwmoving = nb.Nifti1Image(dwframe, self.affine, None)

        self.dataobj[..., index] = np.asanyarray(  # type: ignore[index]
            xform.apply(dwmoving, order=order).dataobj,
            dtype=self.dataobj.dtype,
        )

        r_bvec = (~xform).map([bvec, (0.0, 0.0, 0.0)])
        new_bvec = r_bvec[1] - r_bvec[0]
        if self.gradients is None:
            raise ValueError("No diffusion gradients found in DWI object")
        self.gradients[:3, index] = new_bvec / np.linalg.norm(new_bvec)  # type: ignore[index]

        if self.em_affines is None:
            self.em_affines = np.zeros((self.dataobj.shape[-1], 4, 4))  # type: ignore[index]

        self.em_affines[index] = xform.matrix  # type: ignore[index]

    def to_filename(
        self,
        filename: Path,
        compression: str | None = None,
        compression_opts: int | None = None,
    ) -> None:
        """Write an HDF5 file to disk."""
        filename = Path(filename)
        if not filename.name.endswith(".h5"):
            filename = filename.parent / f"{filename.name}.h5"

        with h5py.File(filename, "w") as out_file:
            out_file.attrs["Format"] = "EMC/DWI"
            out_file.attrs["Version"] = np.uint16(1)
            root = out_file.create_group("/0")
            root.attrs["Type"] = "dwi"
            for f in fields(self):
                if f.name.startswith("_"):
                    continue
                value = getattr(self, f.name)
                if value is not None:
                    root.create_dataset(
                        f.name,
                        data=value,
                        compression=compression,
                        compression_opts=compression_opts,
                    )

    def to_nifti(self, filename: Path, **kwargs: Any) -> None:
        """Write a NIfTI 1.0 file to disk."""
        # 1. Early exit/guard clause for dataobj to satisfy mypy
        if self.dataobj is None:
            raise ValueError("Cannot write to NIfTI because `self.dataobj` is None.")

        insert_b0 = kwargs.get("insert_b0", False)
        if insert_b0:
            if not hasattr(self, "bzero") or self.bzero is None:
                raise ValueError("`insert_b0` is True, but `self.bzero` is None.")

            # Ensure bzero matches the spatial dimensions of dataobj
            b0_data = np.squeeze(self.bzero)
            data = np.concatenate((b0_data[..., np.newaxis], self.dataobj), axis=-1)
        else:
            data = self.dataobj

        nii = nb.Nifti1Image(data, self.affine)
        nii.header.set_xyzt_units(xyz="mm", t="sec")
        nii.to_filename(str(filename))

    @classmethod
    def from_filename(cls, filename: Path) -> "DWI":
        """Read an HDF5 file from disk."""
        with h5py.File(filename, "r") as in_file:
            root = in_file["/0"]
            data = {
                k: np.asanyarray(v) for k, v in root.items() if not k.startswith("_")
            }
        return cls(**data)  # type: ignore[call-arg]


def load(
    filename: Path,
    gradients_file: Path | None = None,
    b0_file: Path | None = None,
    brainmask_file: Path | None = None,
    fmap_file: Path | None = None,
    bvec_file: Path | None = None,
    bval_file: Path | None = None,
    b0_thres: float = 50,
    filepath_parent: Path | None = None,
) -> DWI:
    """Load DWI data.

    Parameters
    ----------
    filename : Path
        Path to the DWI NIfTI file.
    gradients_file : Path, optional
        Path to a combined gradients table file.
    b0_file : Path, optional
        Path to a precomputed b=0 reference.
    brainmask_file : Path, optional
        Path to a brain mask.
    fmap_file : Path, optional
        Path to a fieldmap.
    bvec_file : Path, optional
        Path to a bvec file.
    bval_file : Path, optional
        Path to a bval file.
    b0_thres : float
        Threshold below which a volume is considered b=0.
    filepath_parent : Path, optional
        Parent directory for the internal HDF5 temp file.

    Returns:
    -------
    DWI
        A DWI data object.
    """
    filename = Path(filename)
    if filename.name.endswith(".h5"):
        return DWI.from_filename(filename)

    if gradients_file:
        grad = np.loadtxt(gradients_file, dtype="float32").T

        if bvec_file and bval_file:
            import warnings

            warnings.warn(
                "Gradients table file and b-vec/val files are defined; "
                "dismissing b-vec/val files.",
                stacklevel=2,
            )
    elif bvec_file and bval_file:
        grad = np.vstack(
            (
                np.loadtxt(bvec_file, dtype="float32"),
                np.loadtxt(bval_file, dtype="float32"),
            )
        )
    else:
        raise RuntimeError("A gradients file is necessary")

    img = nb.load(filename)
    fulldata = img.get_fdata(dtype="float32")  # type: ignore[attr-defined]
    retval = DWI(affine=img.affine, _filepath=filepath_parent)  # type: ignore[attr-defined, call-arg]
    gradmsk = grad[-1] > b0_thres
    retval.gradients = grad[..., gradmsk]
    retval.dataobj = fulldata[..., gradmsk]

    if b0_file:
        b0img = nb.load(b0_file)
        retval.bzero = np.asanyarray(b0img.dataobj)  # type: ignore[attr-defined]
    elif not np.all(gradmsk):
        retval.bzero = np.median(fulldata[..., ~gradmsk], axis=3)

    if brainmask_file:
        mask = nb.load(brainmask_file)
        retval.brainmask = np.asanyarray(mask.dataobj)  # type: ignore[attr-defined]

    if fmap_file:
        fmapimg = nb.load(fmap_file)
        retval.fieldmap = fmapimg.get_fdata(  # type: ignore[attr-defined]
            fmapimg, dtype="float32"
        )

    return retval


# --------------------------------------------------------------------------- #
#  LOVO splitting
# --------------------------------------------------------------------------- #


def lovo_split(
    dataset: DWI,
    index: int,
    with_b0: bool = False,
) -> tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]:
    """Produce one fold of LOVO (leave-one-volume-out).

    Parameters
    ----------
    dataset : DWI
        DWI object.
    index : int
        Index of the DWI orientation to be left out.
    with_b0 : bool
        Whether to include the b=0 reference in the training data.

    Returns:
    -------
    train : tuple[np.ndarray, np.ndarray]
        Training DWI data and corresponding gradients.
    test : tuple[np.ndarray, np.ndarray]
        Test 3D map and corresponding b-vector/value.
    """
    if not Path(dataset.get_filename()).exists():
        dataset.to_filename(dataset.get_filename())

    with h5py.File(dataset.get_filename(), "r") as in_file:
        root = in_file["/0"]
        data = np.asanyarray(root["dataobj"])
        gradients = np.asanyarray(root["gradients"])

    mask = np.zeros(data.shape[-1], dtype=bool)
    mask[index] = True

    train_data = data[..., ~mask]
    train_gradients = gradients[..., ~mask]
    test_data = data[..., mask]
    test_gradients = gradients[..., mask]

    if with_b0:
        train_data = np.concatenate(
            (np.asanyarray(dataset.bzero)[..., np.newaxis], train_data),
            axis=-1,
        )
        b0vec = np.zeros((4, 1))
        b0vec[0, 0] = 1
        train_gradients = np.concatenate(
            (b0vec, train_gradients),
            axis=-1,
        )

    return (
        (train_data, train_gradients),
        (test_data, test_gradients),
    )


# --------------------------------------------------------------------------- #
#  TrivialB0Model
# --------------------------------------------------------------------------- #


class TrivialB0Model:
    """A trivial model that returns a *b=0* map always."""

    __slots__ = ("_S0",)

    def __init__(self, S0: np.ndarray | None = None, **kwargs: Any) -> None:
        """Initialize with S0 reference map.

        Parameters
        ----------
        S0 : np.ndarray
            The b=0 reference map.
        """
        if S0 is None:
            raise ValueError("S0 must be provided")
        self._S0 = S0

    def fit(self, *args: Any, **kwargs: Any) -> None:
        """Do nothing."""

    def predict(self, gradient: np.ndarray | None = None, **kwargs: Any) -> np.ndarray:
        """Return the *b=0* map."""
        return self._S0


# --------------------------------------------------------------------------- #
#  Helper functions
# --------------------------------------------------------------------------- #


def _spherical_footprint(radius: int = 3) -> np.ndarray:
    """Generate a binary 3D spherical structuring element.

    Replaces ``skimage.morphology.ball(radius)``.

    Parameters
    ----------
    radius : int
        Radius of the sphere.

    Returns:
    -------
    np.ndarray
        3D boolean array.
    """
    shape = (2 * radius + 1,) * 3
    center = np.array([radius] * 3)
    grid = np.ogrid[: shape[0], : shape[1], : shape[2]]
    distances = (
        (grid[0] - center[0]) ** 2
        + (grid[1] - center[1]) ** 2
        + (grid[2] - center[2]) ** 2
    )
    return distances <= radius * radius


def _advanced_clip(
    data: np.ndarray,
    p_min: float = 35,
    p_max: float = 99.98,
    nonnegative: bool = True,
    dtype: str = "int16",
    invert: bool = False,
) -> np.ndarray:
    """Remove outliers and fit into a given dtype.

    Applies percentiles for clipping images after denoising with a
    median filter.

    Parameters
    ----------
    data : np.ndarray
        Input data.
    p_min : float
        Lower percentile.
    p_max : float
        Upper percentile.
    nonnegative : bool
        Whether to consider only positive values.
    dtype : str
        Target dtype.
    invert : bool
        Whether to invert the data.

    Returns:
    -------
    np.ndarray
        Clipped and normalized data.
    """
    denoised = ndimage.median_filter(data, footprint=_spherical_footprint(3))

    if nonnegative:
        masked = denoised[denoised > 0]
    else:
        masked = denoised
    a_min = np.percentile(masked, p_min)
    a_max = np.percentile(masked, p_max)

    data = np.clip(data, a_min=a_min, a_max=a_max)
    data -= data.min()
    data /= data.max()

    if invert:
        data = 1.0 - data

    if dtype in ("uint8", "int16"):
        data = np.round(255 * data).astype(dtype)

    return data


def _to_nifti(
    data: np.ndarray,
    affine: np.ndarray,
    filename: Path,
    clip: bool = True,
) -> None:
    """Save data as NIfTI file.

    Parameters
    ----------
    data : np.ndarray
        Image data.
    affine : np.ndarray
        Affine transformation matrix.
    filename : Path
        Output filename.
    clip : bool
        Whether to clip intensities.
    """
    data = np.squeeze(data)
    if clip:
        data = _advanced_clip(data)
    nii = nb.Nifti1Image(data, affine, None)
    nii.header.set_sform(affine, code=1)
    nii.header.set_qform(affine, code=1)
    nii.to_filename(filename)


def _sort_dwdata_indices(seed: int | bool | None, dwi_vol_count: int) -> np.ndarray:
    """Sort the DWI data volume indices.

    Parameters
    ----------
    seed : int or bool or None
        Seed for the random number generator.
    dwi_vol_count : int
        Number of DWI volumes.

    Returns:
    -------
    np.ndarray
        Shuffled index order.
    """
    _seed = None
    if seed or seed == 0:
        _seed = 20210324 if seed is True else seed

    rng = np.random.default_rng(_seed)
    index_order = np.arange(dwi_vol_count)
    rng.shuffle(index_order)
    return index_order


def _prepare_brainmask_data(
    brainmask: np.ndarray | None,
    affine: np.ndarray,
) -> str | None:
    """Prepare the brainmask data: save to disk.

    Parameters
    ----------
    brainmask : np.ndarray or None
        Brainmask data.
    affine : np.ndarray
        Affine transformation matrix.

    Returns:
    -------
    str or None
        Path to the brainmask NIfTI file.
    """
    if brainmask is None:
        return None
    _, bmask_path = mkstemp(suffix="_bmask.nii.gz")
    nb.Nifti1Image(brainmask.astype("uint8"), affine, None).to_filename(bmask_path)
    return bmask_path


def _prepare_kwargs(dwdata: DWI, kwargs: dict[str, Any]) -> None:
    """Prepare keyword arguments from DWI data.

    Modifies kwargs in-place.

    Parameters
    ----------
    dwdata : DWI
        DWI data object.
    kwargs : dict
        Keyword arguments to update.
    """
    if dwdata.brainmask is not None:
        kwargs["mask"] = dwdata.brainmask

    if hasattr(dwdata, "bzero") and dwdata.bzero is not None:
        kwargs["S0"] = _advanced_clip(dwdata.bzero)

    if hasattr(dwdata, "gradients"):
        kwargs["gtab"] = dwdata.gradients


def _prepare_registration_data(
    dwframe: np.ndarray,
    predicted: np.ndarray,
    affine: np.ndarray,
    vol_idx: int,
    dirname: Path,
    reg_target_type: str,
) -> tuple[Path, Path]:
    """Save the fixed and moving images for registration.

    Parameters
    ----------
    dwframe : np.ndarray
        Actual DWI frame.
    predicted : np.ndarray
        Predicted (synthetic) frame.
    affine : np.ndarray
        Affine matrix.
    vol_idx : int
        Volume index.
    dirname : Path
        Output directory.
    reg_target_type : str
        Registration target type ("b0" or "dwi").

    Returns:
    -------
    fixed : Path
        Fixed image path.
    moving : Path
        Moving image path.
    """
    moving = dirname / f"moving{vol_idx:05d}.nii.gz"
    fixed = dirname / f"fixed{vol_idx:05d}.nii.gz"
    _to_nifti(dwframe, affine, moving)
    _to_nifti(predicted, affine, fixed, clip=reg_target_type == "dwi")
    return fixed, moving


# --------------------------------------------------------------------------- #
#  Registration
# --------------------------------------------------------------------------- #


def _run_registration(
    fixed: Path,
    moving: Path,
    bmask_img: str | None,
    em_affines: np.ndarray | None,
    affine: np.ndarray,
    shape: tuple[int, ...],
    bval: int,
    fieldmap: np.ndarray | None,
    i_iter: int,
    vol_idx: int,
    dirname: Path,
    reg_target_type: str,
    align_kwargs: dict[str, Any] | None = None,
) -> Affine:
    """Register the moving image to the fixed image using ANTs.

    Parameters
    ----------
    fixed : Path
        Fixed image filename.
    moving : Path
        Moving image filename.
    bmask_img : str or None
        Brainmask image path.
    em_affines : np.ndarray or None
        Estimated eddy motion affine matrices.
    affine : np.ndarray
        Affine transformation matrix.
    shape : tuple
        Shape of the DWI frame.
    bval : int
        b-value of the corresponding DWI volume.
    fieldmap : np.ndarray or None
        Fieldmap (not implemented).
    i_iter : int
        Iteration number.
    vol_idx : int
        DWI frame index.
    dirname : Path
        Working directory.
    reg_target_type : str
        Target registration type ("b0" or "dwi").
    align_kwargs : dict or None
        Additional registration parameters.

    Returns:
    -------
    Affine
        Registration transformation.
    """
    align_kwargs = align_kwargs or {}
    stages = _build_stages(reg_target_type, i_iter, fixed, moving)

    output_prefix = f"antsReg_{vol_idx:05d}_"

    initial_moving_transform = None
    if em_affines is not None and np.any(em_affines[vol_idx, ...]):
        reference = namedtuple("ImageGrid", ("shape", "affine"))(  # type: ignore[call-arg]
            shape=shape, affine=affine
        )
        if fieldmap:
            raise NotImplementedError
        initial_xform = Affine(matrix=em_affines[vol_idx], reference=reference)
        mat_file = dirname / f"init_{i_iter}_{vol_idx:05d}.mat"
        initial_xform.to_filename(mat_file, fmt="itk")
        initial_moving_transform = ants.ants_registration_initial_moving_transform(
            initial_moving_transform=str(mat_file),
        )

    masks_param = None
    if bmask_img:
        masks_param = ants.ants_registration_masks(fixed_mask=bmask_img)

    result = ants.ants_registration(
        stages=stages,
        dimensionality=3,
        output=output_prefix,
        interpolation="Linear",
        collapse_output_transforms=True,
        initialize_transforms_per_stage=False,
        initial_moving_transform=initial_moving_transform,
        masks=masks_param,
        winsorize_image_intensities=ants.ants_registration_winsorize_image_intensities(
            lower_quantile=0.0001,
            upper_quantile=0.9998,
        ),
        verbose=True,
        **align_kwargs,
    )

    # Read output transform
    transform_file = result.generic_affine
    xform = Affine(
        ITKLinearTransform.from_filename(transform_file).to_ras(
            reference=fixed, moving=moving
        ),
    )

    # Debugging: generate aligned file
    xform.apply(moving, reference=fixed).to_filename(
        dirname / f"aligned{vol_idx:05d}_{int(bval):04d}.nii.gz"
    )

    return xform


# --------------------------------------------------------------------------- #
#  EddyMotionEstimator
# --------------------------------------------------------------------------- #


class EddyMotionEstimator:
    """Estimates rigid-body head-motion and eddy-current distortions."""

    @staticmethod
    def estimate(
        dwdata: DWI,
        *,
        filepath_parent: Path | None = None,
        align_kwargs: dict[str, Any] | None = None,
        models: list[str] | None = None,
        n_jobs: int | None = None,
        seed: int | bool | None = None,
        **kwargs: Any,
    ) -> np.ndarray | None:
        """Estimate head-motion and eddy currents.

        Parameters
        ----------
        dwdata : DWI
            The target DWI dataset. Modified in-place with estimated
            transforms in ``em_affines`` and rotated b-vectors in
            ``gradients``.
        filepath_parent : Path or None
            Parent directory for the internal HDF5 temp file.
        align_kwargs : dict or None
            Parameters to configure image registration.
        models : list of str or None
            Diffusion models to use. Default is ``["b0"]``.
        omp_nthreads : int or None
            Maximum number of threads.
        n_jobs : int or None
            Number of parallel jobs.
        seed : int or bool or None
            Seed for reproducibility.

        Returns:
        -------
        np.ndarray
            Array of 4x4 affine matrices encoding the estimated
            deformations.
        """
        if dwdata.affine is None:
            raise ValueError("dwdata.affine cannot be None.")

        if filepath_parent is not None:
            dwdata._filepath = filepath_parent

        align_kwargs = align_kwargs or {}
        models = models or ["b0"]

        index_order = _sort_dwdata_indices(seed, len(dwdata))

        len(models)
        for i_iter, model in enumerate(models):
            reg_target_type = (
                "dwi"
                if model.lower() not in ("b0", "s0", "avg", "average", "mean")
                else "b0"
            )

            bmask_img = _prepare_brainmask_data(dwdata.brainmask, dwdata.affine)
            _prepare_kwargs(dwdata, kwargs)

            single_model = model.lower() in (
                "b0",
                "s0",
                "avg",
                "average",
                "mean",
            ) or model.lower().startswith("full")

            dwmodel: TrivialB0Model | None = None
            if single_model:
                if model.lower().startswith("full"):
                    model = model[4:]
                dwmodel = TrivialB0Model(**kwargs)
                dwmodel.fit(dwdata.dataobj, n_jobs=n_jobs)

            with TemporaryDirectory() as tmp_dir:
                print(f"Processing in <{tmp_dir}>")
                ptmp_dir = Path(tmp_dir)
                for i in index_order:
                    data_train, data_test = lovo_split(dwdata, i, with_b0=True)

                    assert dwmodel is not None
                    predicted = dwmodel.predict(data_test[1])

                    fixed, moving = _prepare_registration_data(
                        data_test[0],
                        predicted,
                        dwdata.affine,
                        i,
                        ptmp_dir,
                        reg_target_type,
                    )
                    if dwdata.dataobj is None:
                        raise ValueError("Expected ndarray dataobj, got None")
                    xform = _run_registration(
                        fixed,
                        moving,
                        bmask_img,
                        dwdata.em_affines,
                        dwdata.affine,
                        dwdata.dataobj.shape[:3],
                        data_test[1][3],
                        dwdata.fieldmap,
                        i_iter,
                        i,
                        ptmp_dir,
                        reg_target_type,
                        align_kwargs,
                    )

                    dwdata.set_transform(i, xform.matrix)

        return dwdata.em_affines
