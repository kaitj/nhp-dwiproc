"""Connectivity stage command implementation."""

from functools import partial
from pathlib import Path

import typer

from nhp_dwiproc import app
from nhp_dwiproc import config as cfg_
from nhp_dwiproc.cli import utils as cli_utils


def command(
    ctx: typer.Context,
    opts_config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML-formatted configuration file. [default: "
        f"{cfg_.GlobalOptsConfig.config}]",
        exists=True,
        dir_okay=False,
        file_okay=True,
        resolve_path=True,
    ),
    opts_threads: int | None = typer.Option(
        None,
        "--threads",
        help=f"Number of threads to use. [default: {cfg_.GlobalOptsConfig.threads}]",
    ),
    opts_index_path: Path | None = typer.Option(
        None,
        "--index-path",
        help="Path to read / write bids2table index. [default: "
        f"{cfg_.GlobalOptsConfig.index_path}]",
    ),
    opts_runner: cfg_.shared.Runner | None = typer.Option(
        None,
        "--runner",
        help=f"Type of runner to run workflow. [default: '{cfg_.RunnerConfig.name}']",
    ),
    opts_images: str | None = typer.Option(
        None,
        "--runner-images",
        callback=cli_utils.json_dict_callback,
        help="String dictionary, mapping container overrides."
        f"[default: {cfg_.RunnerConfig.images}]",
    ),
    opts_graph: bool | None = typer.Option(
        None,
        "--graph",
        help="Print mermaid diagram of workflow. [default: "
        f"{cfg_.GlobalOptsConfig.graph}]",
    ),
    opts_seed_number: int | None = typer.Option(
        None,
        "--seed-num",
        help="Fixed seed to use for generating reproducible results. [default: "
        f"{cfg_.GlobalOptsConfig.seed_number}]",
    ),
    opts_work_dir: Path | None = typer.Option(
        None,
        "--work-dir",
        help=f"Working directory. [default: '{cfg_.GlobalOptsConfig.work_dir}']",
        file_okay=False,
        resolve_path=True,
    ),
    opts_work_keep: bool | None = typer.Option(
        None,
        "--work-keep",
        help=f"Keep working directory. [default: {cfg_.GlobalOptsConfig.work_keep}]",
    ),
    query_participant: str | None = typer.Option(
        None,
        "--participant-query",
        help="String query for 'subject' & 'session'. [default: "
        f"{cfg_.QueryConfig.participant}]",
    ),
    conn_method: cfg_.connectivity.ConnectivityMethod | None = typer.Option(
        None,
        "--method",
        help="Type of connectivity analysis to perform. [default: "
        f"'{cfg_.ConnectivityConfig.method}']",
    ),
    conn_atlas: str | None = typer.Option(
        None,
        "--atlas",
        help="Volumetric atlas (assumed to be in same space) to compute connectivity "
        f"matrix. [default: {cfg_.connectivity.ConnectomeConfig.atlas}]",
    ),
    conn_radius: float | None = typer.Option(
        None,
        "--radius",
        help="Distance (in mm) to nearest parcel. [default: "
        f"{cfg_.connectivity.ConnectomeConfig.radius}]",
    ),
    conn_voxel_size: list[float] | None = typer.Option(
        None,
        "--vox-mm",
        help="Isotropic voxel size (in mm) or list of voxel sizes "
        f"(repeat argument) for tract map. [default: "
        f"{cfg_.connectivity.TractMapConfig.voxel_size}]",
    ),
    conn_tract_query: str | None = typer.Option(
        None,
        "--tract-query",
        help="String query for tract-associated BIDS entities; associated ROIs should "
        "contain description entities of 'include', 'exclude', 'stop' for respective "
        f"ROIs. [default: {cfg_.connectivity.TractMapConfig.tract_query}]",
    ),
    conn_surface_query: str | None = typer.Option(
        None,
        "--surf-query",
        help="String query for surface-associated BIDS entities to perform "
        "ribbon-constrained mapping of streamlines; surface type (e.g. white, pial, "
        "etc.) will be automatically identified. "
        f"[default: {cfg_.connectivity.TractMapConfig.surface_query}]",
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="Verbosity (-v, -vv, -vvv)."),
) -> None:
    """Connectivity stage-level."""
    local_vars = locals()
    builder = partial(
        cfg_.utils.build_config, ctx_params=ctx.params, cfg_file=opts_config
    )
    mapper = partial(cfg_.utils.map_param, vars_dict=local_vars)
    # Global options
    ctx.obj.cfg.opts = cli_utils.build_global_opts(
        ctx_params=ctx.params, cfg_file=opts_config
    )
    # Stage specific options
    conn_map = mapper("conn_", "opts.")
    conn_map.update({"conn_method": "method", "query_participant": "query.participant"})
    method_map: dict[str, dict[object, type]] = {
        "method": {
            "connectome": cfg_.connectivity.ConnectomeConfig,
            "tract": cfg_.connectivity.TractMapConfig,
        },
    }
    ctx.obj.cfg.connectivity = builder(
        cfg_class=cfg_.connectivity.ConnectivityConfig,
        cfg_key="connectivity",
        include_only=list(conn_map.keys()),
        cli_map=conn_map,
        dynamic_method_map=method_map,
    )
    # Verbosity
    ctx.obj.log_level = cli_utils.setup_logging(verbose)
    # Setup styx
    logger, runner = app.initialize(
        output_dir=ctx.obj.cfg.output_dir, global_opts=ctx.obj.cfg.opts
    )
    cli_utils.finalize_stage(ctx=ctx.obj, logger=logger)
    app.analysis_levels.connectivity(
        input_dir=ctx.obj.cfg.input_dir,
        output_dir=ctx.obj.cfg.output_dir,
        conn_opts=ctx.obj.cfg.connectivity,
        global_opts=ctx.obj.cfg.opts,
        runner=runner,
        logger=logger,
    )
