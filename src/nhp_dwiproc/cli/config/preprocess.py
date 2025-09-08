"""Preprocessing configuration."""

from dataclasses import dataclass, field
from enum import Enum

from .shared import BaseConfig


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
    estimator: DenoiseEstimator = DenoiseEstimator.exp2


@dataclass
class UnringConfig(BaseConfig):
    """Gibbs' unringing config."""

    axes: list[int] = field(default_factory=lambda: [0, 1])


class DistortionMethod(str, Enum):
    """Distortion correction method options."""

    topup = "topup"
    fieldmap = "fieldmap"
    eddymotion = "eddymotion"


@dataclass
class DistortionConfig:
    """Distortion configuration."""

    method: DistortionMethod = DistortionMethod.topup


@dataclass
class TopupConfig(BaseConfig):
    """FSL's TOPUP configuration."""

    config: str = "b02b0_macaque"


class EddySLMModel(str, Enum):
    """FSL's Eddy SLM model."""

    none = None
    linear = "linear"
    quadratic = "quadratic"


@dataclass
class EddyConfig(BaseConfig):
    """FSL's Eddy configuration."""

    slm: EddySLMModel = EddySLMModel.none
    cnr: bool = False
    repol: bool = False
    residuals: bool = False
    shelled: bool = False


@dataclass
class EddyMotionConfig:
    """Eddytmotion configuration."""

    iters: int = 2


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

    metric: RegistrationMetric = RegistrationMetric.NMI
    iters: str = "50x50"
    init: RegistrationInit = RegistrationInit.identity
