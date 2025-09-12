"""Reconstruction configuration."""

from dataclasses import dataclass, field
from enum import Enum

from .shared import BaseConfig, QueryConfig


class TractographyMethod(str, Enum):
    """Tractography reconstruction method."""

    wm = "wm"
    act = "act"


@dataclass
class TractographyACTConfig:
    """ACT option configuration."""

    backtrack: bool = False
    no_crop_gmwmi: bool = False


@dataclass
class TractographyConfig(BaseConfig):
    """Tractography configuration."""

    single_shell: bool = False
    shells: list[int] | None = None
    lmax: list[int] | None = None
    steps: float | None = None
    method: str = TractographyMethod.wm.value
    opts: TractographyACTConfig | None = None
    cutoff: float = 0.1
    streamlines: int = 10_000


@dataclass
class ReconstructionConfig:
    """Reconstruction configuration."""

    query: QueryConfig = field(default_factory=QueryConfig)
    tractography: TractographyConfig = field(default_factory=TractographyConfig)
