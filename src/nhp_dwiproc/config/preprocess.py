"""Preprocessing configuration."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from nhp_dwiproc.config.shared import BaseConfig, QueryConfig


@dataclass
class MetadataConfig:
    """Metadata config."""

    pe_dirs: list[str] | None = None
    echo_spacing: float | None = None


class DenoiseEstimator(str, Enum):
    """Denoise estimator options."""

    exp1 = "Exp1"
    exp2 = "Exp2"


@dataclass
class DenoiseConfig(BaseConfig):
    """Denoise config."""

    map_: bool = False
    estimator: str = DenoiseEstimator.exp2.value


@dataclass
class UnringConfig(BaseConfig):
    """Gibbs' unringing config."""

    axes: Sequence[int] | None = None


@dataclass
class TopupConfig(BaseConfig):
    """FSL's TOPUP configuration."""

    config: str = "b02b0_macaque"


class EddySLMModel(str, Enum):
    """FSL's Eddy SLM model."""

    linear = "linear"
    quadratic = "quadratic"


@dataclass
class EddyConfig(BaseConfig):
    """FSL's Eddy configuration."""

    slm: Literal["none", "linear", "quadratic"] | None = None
    cnr: bool = False
    repol: bool = False
    residuals: bool = False
    shelled: bool = False


@dataclass
class EddyMotionConfig(BaseConfig):
    """Eddymotion configuration."""

    iters: int = 2


@dataclass
class FugueConfig(BaseConfig):
    """Fugue configuration."""

    smooth: float | None = None


class UndistortionMethod(str, Enum):
    """Distortion correction method choices."""

    topup = "topup"
    fieldmap = "fieldmap"
    eddymotion = "eddymotion"
    fugue = "fugue"


@dataclass
class UndistortionOpts:
    """Distortion correction method options."""

    topup: TopupConfig | None = field(default_factory=TopupConfig)
    eddy: EddyConfig | None = field(default_factory=EddyConfig)
    eddymotion: EddyMotionConfig | None = field(default_factory=EddyMotionConfig)
    fugue: FugueConfig | None = field(default_factory=FugueConfig)


@dataclass
class UndistortionConfig:
    """Distortion configuration."""

    method: str = UndistortionMethod.topup.value
    opts: UndistortionOpts = field(default_factory=UndistortionOpts)


@dataclass
class BiascorrectConfig(BaseConfig):
    """Bias correction configuration."""

    spacing: float = 100.0
    iters: int = 1000
    shrink: int = 4


class RegistrationMetric(str, Enum):
    """Registration metrics."""

    SSD = "SSD"
    MI = "MI"
    NMI = "NMI"
    MAHAL = "MAHAL"


class RegistrationInit(str, Enum):
    """Initialization method."""

    identity = "identity"
    image_centers = "image-centers"


@dataclass
class RegistrationConfig(BaseConfig):
    """Registration configuration."""

    metric: str = RegistrationMetric.NMI.value
    iters: str = "50x50"
    init: str = RegistrationInit.identity.value


@dataclass
class PreprocessConfig:
    """Preprocessing configuration."""

    query: QueryConfig = field(default_factory=QueryConfig)
    metadata: MetadataConfig = field(default_factory=MetadataConfig)
    denoise: DenoiseConfig = field(default_factory=DenoiseConfig)
    unring: UnringConfig = field(default_factory=UnringConfig)
    undistort: UndistortionConfig = field(default_factory=UndistortionConfig)
    biascorrect: BiascorrectConfig = field(default_factory=BiascorrectConfig)
    registration: RegistrationConfig = field(default_factory=RegistrationConfig)
