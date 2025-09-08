"""Reconstruction configuration."""

from dataclasses import dataclass
from enum import Enum

from .shared import BaseConfig


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
    method: TractographyMethod = TractographyMethod.act
    opts: TractographyACTConfig | None = None
    cutoff: float = 0.1
    streamlines: int = 10_000
