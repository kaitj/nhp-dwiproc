"""Shared type aliases for nhp-dwiproc."""

from pathlib import Path
from typing import TypeAlias

from niwrap import DockerRunner, LocalRunner, SingularityRunner
from styxpodman import PodmanRunner

StrPath: TypeAlias = str | Path
"""String or Path type alias."""

BaseRunner: TypeAlias = DockerRunner | LocalRunner | PodmanRunner | SingularityRunner
"""Union of concrete runner types (excludes GraphRunner middleware)."""
