"""Connectivity configuration."""

from dataclasses import dataclass, field
from enum import Enum

from nhp_dwiproc.config.shared import QueryConfig


@dataclass
class TractMapConfig:
    """Tract mapping configuration."""

    voxel_size: list[float] | None = None
    tract_query: str | None = None
    surface_query: str | None = None


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

    query: QueryConfig = field(default_factory=QueryConfig)
    method: str = ConnectivityMethod.connectome.value
    opts: ConnectomeConfig | TractMapConfig = field(default_factory=ConnectomeConfig)
