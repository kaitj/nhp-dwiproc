"""Shared Configuration classes for CLI."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Runner(str, Enum):
    """Runner config options."""

    local = "local"
    docker = "docker"
    podman = "podman"
    appainer = "apptainer"
    singularity = "singularity"


@dataclass
class RunnerConfig:
    """Runner configuration."""

    type_: Runner = Runner.local
    images: dict[str, str | Path] | None = None


@dataclass
class GlobalConfig:
    """Shared configuration across all analysis levels."""

    config: Path | None = None
    threads: int = 1
    index_path: Path | None = None
    runner: RunnerConfig = field(default_factory=RunnerConfig)
    graph: bool = False
    seed_number: int = 99
    work_dir: Path = Path("styx_tmp")
    work_keep: bool = False
    b0_thresh: int = 10


@dataclass
class QueryConfig:
    """Query configuration."""

    participant: str | None = None
    dwi: str | None = None
    t1w: str | None = None
    mask: str | None = None
    fmap: str | None = None


@dataclass
class BaseConfig:
    """Base processing step configuration."""

    skip: bool = False
