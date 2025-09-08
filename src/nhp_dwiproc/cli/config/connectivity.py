"""Connectivity configuration."""

from dataclasses import dataclass, field
from enum import Enum


@dataclass
class TractMapConfig:
    """Tract mapping configuration."""

    voxel_size: list[float] | None = None
    tract: str | None = None
    surface: str | None = None


@dataclass
class ConnectomeConfig:
    """Connectome configuration."""

    atlas: str | None = None
    radius: float = 2.0


class ConnectivityMethod(str, Enum):
    """Connectivity method to perform."""

    connectome = "connectome"
    tract = "tract"


@dataclass
class ConnectivityConfig:
    """Connectivity configuration."""

    method: ConnectivityMethod = ConnectivityMethod.connectome
    opts: TractMapConfig | ConnectomeConfig = field(default_factory=ConnectomeConfig)
