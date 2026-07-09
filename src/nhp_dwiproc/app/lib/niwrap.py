"""Niwrap helper utilities (lifted from niwrap-helper).

These functions were previously provided by the niwrap-helper package.
They are lifted here to allow upgrading to niwrap 0.9.x, which bundles
all plugin packages as transitive dependencies.
"""

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Literal, NamedTuple

import bids2table as b2t
import niwrap
import pyarrow as pa
import pyarrow.parquet as pq
from niwrap import (
    GraphRunner,
)
from styxpodman import PodmanRunner

from nhp_dwiproc.app.lib.types import BaseRunner, StrPath

# --- Constants ---

_LOG_LEVELS = [logging.WARNING, logging.INFO, logging.DEBUG]

RunnerType = Literal["local", "docker", "podman", "singularity"]

_RUNNER_EXECUTABLES: list[tuple[RunnerType, list[str]]] = [
    ("podman", ["podman"]),
    ("docker", ["docker"]),
    ("singularity", ["apptainer", "singularity"]),
]

_WORK_ROOT: Path | None = None


def _work_root(tmp_dir: str = "styx_tmp") -> Path:
    """Return the shared work-dir root, creating it on first use.

    A single temp directory serves as the parent for both the runner's
    data_dir and any scratch folders created via :func:`generate_exec_folder`,
    so cleanup covers everything in one sweep.

    Args:
        tmp_dir: Base directory name. Defaults to ``'styx_tmp'``.

    Returns:
        A Path to the work root.

    """
    global _WORK_ROOT
    if _WORK_ROOT is not None and _WORK_ROOT.exists():
        return _WORK_ROOT

    _WORK_ROOT = Path(tempfile.mkdtemp(prefix=tmp_dir + "_"))
    return _WORK_ROOT


def generate_exec_folder(suffix: str = "exec") -> Path:
    """Create a fresh scratch directory for intermediate outputs.

    Returns a unique directory under the work-root's ``scratch/``
    subdirectory. Writes here are guaranteed not to collide with
    the runner's data_dir.

    Args:
        suffix: Prefix for the generated directory name.

    Returns:
        A unique temporary directory path.

    """
    scratch = _work_root() / "scratch"
    scratch.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=suffix + "_", dir=scratch))


class StyxContext(NamedTuple):
    """Styx execution context with logger, runner, and verbosity."""

    logger: logging.Logger
    runner: BaseRunner | GraphRunner
    verbose: bool


# --- resolve_runner ---


def resolve_runner(
    runner: RunnerType | Literal["auto"] = "auto",
) -> tuple[RunnerType, str]:
    """Resolve runner selection, auto-detecting if needed.

    When runner is ``"auto"``, checks for available container runtimes
    on :envvar:`PATH` in order of preference: podman > docker >
    apptainer/singularity > local.

    Args:
        runner: Runner type or ``"auto"`` for auto-detection.

    Returns:
        A 2-tuple of (runner_type, executable_name).

    """
    if runner != "auto":
        return runner, runner  # type: ignore[return-value]

    for runner_type, executables in _RUNNER_EXECUTABLES:
        for exe in executables:
            if shutil.which(exe):
                return runner_type, exe

    return "local", "local"


# --- bids_path ---


def bids_path(
    directory: bool = False, return_path: bool = False, **entities
) -> StrPath:
    """Generate BIDS name / path.

    Wraps :func:`bids2table.format_bids_path`.

    Args:
        directory: Flag to return only parent directories -- mutually exclusive with
            ``return_path``. If both set to False, only returns the file name.
        return_path: Flag to return full path -- mutually exclusive with
            ``directory``. If both set to False, only returns the file name.
        **entities: BIDS entities provided as keyword arguments to be used for
            formulating the BIDS filename / filepath.

    Returns:
        A BIDS-formatted filename (str), parent directory (Path), or full path
        (Path), depending on the flags.

    Raises:
        ValueError: If both ``directory`` and ``return_path`` are True.
    """
    if directory and return_path:
        raise ValueError("Only one of 'directory' or 'return_path' can be True")
    name = b2t.format_bids_path(entities)
    return name.parent if directory else name if return_path else name.name


# --- cleanup ---


def cleanup() -> None:
    """Clean up after completing run.

    Removes the runner's temporary data directory.
    """
    runner = niwrap.get_global_runner()
    base_runner = runner.base if isinstance(runner, GraphRunner) else runner
    shutil.rmtree(base_runner.data_dir)


# --- save ---


def save(files: Path | list[Path], out_dir: Path) -> None:
    """Copy niwrap outputted file(s) to specified output directory.

    Args:
        files: Path or list of paths to save.
        out_dir: Output directory to save file(s) to.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    for file in [files] if isinstance(files, (str, Path)) else files:
        shutil.copy2(file, out_dir / Path(file).name)


# --- get_bids_table ---


def get_bids_table(
    dataset_dir: StrPath,
    b2t_index: StrPath | None = None,
    max_workers: int | None = 0,
    verbose: bool = False,
) -> pa.Table:
    """Get and return BIDS table for a given dataset.

    Args:
        dataset_dir: Path to dataset directory.
        b2t_index: Path to bids2table parquet table. If provided and the file exists
            the parquet table will be used. If ``None`` or the file does not exist,
            the dataset directory will be indexed.
        max_workers: Number of indexing processes to run in parallel.
            Setting ``max_workers=0`` (the default) uses the main process only.
            Setting ``max_workers=None`` starts as many workers as there are
            available CPUs.
        verbose: Show verbose messages.

    Returns:
        A concatenated Arrow table index for all BIDS datasets.
    """
    ds_path = Path(dataset_dir)

    # Load / generate table
    b2t_fp = ds_path / b2t_index if b2t_index else None
    if b2t_fp and b2t_fp.exists():
        table = pq.read_table(b2t_fp)
    else:
        tables = b2t.batch_index_dataset(
            b2t.find_bids_datasets(ds_path),  # type: ignore[arg-type]
            max_workers=max_workers,
            show_progress=verbose,
        )
        table = pa.concat_tables(tables)

    if "extra_entities" not in table.column_names:
        return table

    # Expand "extra_entities"
    extra_entities = table["extra_entities"].to_pylist()
    extra_entities_dicts = []
    all_keys: set = set()
    for ent in extra_entities:
        d = dict(ent) if isinstance(ent, list) else {}
        all_keys.update(d.keys())
        extra_entities_dicts.append(d)
    if not all_keys:
        return table
    all_keys = set(sorted(all_keys))
    rows = [{k: d.get(k, None) for k in all_keys} for d in extra_entities_dicts]
    extra_entities_table = pa.Table.from_pylist(rows).append_column(
        "path", table["path"]
    )
    # Conditional sorting to ensure deterministic join
    paths_main = table["path"].to_pylist()
    paths_extra = extra_entities_table["path"].to_pylist()
    if paths_main != paths_extra:
        table = table.sort_by([("path", "ascending")])
        extra_entities_table = extra_entities_table.sort_by([("path", "ascending")])
    # Append only new columns
    existing = set(table.column_names)
    table = table.drop(["extra_entities"])
    for name in extra_entities_table.column_names:
        if name != "path" and name not in existing:
            table = table.append_column(name, extra_entities_table[name])
    return table


# --- setup_styx ---


def setup_styx(
    runner: RunnerType | Literal["auto"] = "auto",
    tmp_env: str = "LOCAL",
    tmp_dir: str = "styx_tmp",
    image_overrides: dict[str, str] | None = None,
    graph_runner: bool = False,
    verbose: int = 1,
    *args,
    **kwargs,
) -> StyxContext:
    """Setup Styx runner.

    Args:
        runner: Type of runner to use. Choices include
            ``['local', 'docker', 'podman', 'singularity', 'apptainer']``.
            Defaults to ``'auto'`` which auto-detects the first available
            container runtime on :envvar:`PATH`.
        tmp_env: Environment variable to query for temporary folder.
            Defaults to ``'LOCAL'``.
        tmp_dir: Working directory to output to.
            Defaults to ``'{tmp_env}/tmp_dir'``.
        image_overrides: Dictionary containing overrides for container tags.
        graph_runner: Flag to make use of GraphRunner middleware.
        verbose: Verbosity level (0=WARNING, 1=INFO, 2+=DEBUG).
            Defaults to ``1`` (INFO).
        *args: Additional arguments to pass
        **kwargs: Additional keyword arguments to pass

    Returns:
        A :class:`StyxContext` named-tuple containing the configured logger,
        the initialized runner (optionally wrapped in GraphRunner), and a
        boolean indicating whether verbose mode is active.
    """
    runner_type, runner_exec = resolve_runner(runner)

    match runner_type:
        case "local":
            niwrap.use_local(*args, **kwargs)
        case "docker":
            niwrap.use_docker(
                docker_executable=runner_exec,
                image_overrides=image_overrides,
                *args,
                **kwargs,
            )
        case "podman":
            niwrap.set_global_runner(
                runner=PodmanRunner(
                    podman_executable=runner_exec,
                    image_overrides=image_overrides,
                    *args,
                    **kwargs,
                )
            )
        case "singularity" | "apptainer":
            niwrap.use_singularity(
                singularity_executable=runner_exec,
                image_overrides=image_overrides,
                *args,
                **kwargs,
            )

    styx_runner = niwrap.get_global_runner()

    # Working directory management — use mkdtemp inside the work root
    _work_root(tmp_dir)
    if _WORK_ROOT is None:
        raise ValueError("Expected working directory is None")
    data_parent = _WORK_ROOT / "niwrap"
    data_parent.mkdir(parents=True, exist_ok=True)
    styx_runner.data_dir = Path(tempfile.mkdtemp(dir=data_parent))

    # Logger setup — verbose-aware level + handler
    log_level = _LOG_LEVELS[min(verbose, len(_LOG_LEVELS) - 1)]
    styx_logger = logging.getLogger(styx_runner.logger_name)
    styx_logger.setLevel(log_level)
    if not styx_logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(name)s - %(message)s"))
        styx_logger.addHandler(handler)

    if graph_runner:
        niwrap.use_graph(styx_runner)
        styx_runner = niwrap.get_global_runner()

    return StyxContext(
        logger=styx_logger,
        runner=styx_runner,  # type: ignore[arg-type]
        verbose=verbose > 0,
    )
