"""Reconstruction stage command implementation."""

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
    query_dwi: str | None = typer.Option(
        None,
        "--dwi-query",
        help="String query for DWI-associated BIDS entities. [default: "
        f"{cfg_.QueryConfig.dwi}]",
    ),
    query_t1w: str | None = typer.Option(
        None,
        "--t1w-query",
        help="String query for T1w-associated BIDS entities. [default: "
        f"{cfg_.QueryConfig.t1w}]",
    ),
    query_mask: str | None = typer.Option(
        None,
        "--mask-query",
        help="String query for custom mask-associated BIDS entities. [default: "
        f"{cfg_.QueryConfig.mask}]",
    ),
    tract_single_shell: bool | None = typer.Option(
        None,
        "--single-shell",
        help="Indicate single-shell data. [default: "
        f"{cfg_.reconstruction.TractographyConfig.single_shell}]",
    ),
    tract_shells: list[int] | None = typer.Option(
        None,
        "--shells",
        help="b-value of shells (b=0 must be explicitly included); invoke multiple "
        "times for multiple shells. "
        f"[default: {cfg_.reconstruction.TractographyConfig.shells}]",
    ),
    tract_lmax: list[int] | None = typer.Option(
        None,
        "--lmax",
        help="Maximum harmonic degree for each shell (b=0 must be explicitly "
        "included); invoke multiple times for multiple shells."
        f"[default: {cfg_.reconstruction.TractographyConfig.lmax}]",
    ),
    tract_steps: float | None = typer.Option(
        None,
        "--steps",
        help="Step size (in mm) for tractography sampling [default: 0.5 x voxel_size].",
    ),
    tract_cutoff: float | None = typer.Option(
        None,
        "--cutoff",
        help="FOD cutoff amplitude for track termination. [default: "
        f"{cfg_.reconstruction.TractographyConfig.cutoff}]",
    ),
    tract_streamlines: int | None = typer.Option(
        None,
        "--streamlines",
        help="Number of streamlines to select. [default: "
        f"{cfg_.reconstruction.TractographyConfig.streamlines}]",
    ),
    tract_max_length: float | None = typer.Option(
        None,
        "--max-length",
        help="Maximum length for a given tract. [default: 100 x voxel_size]",
    ),
    tract_method: cfg_.reconstruction.TractographyMethod | None = typer.Option(
        None,
        "--tractography-method",
        help="Tractography seeding method. [default: "
        f"{cfg_.reconstruction.TractographyConfig.method}]",
    ),
    tract_act_backtrack: bool | None = typer.Option(
        None,
        "--tractography-act-backtrack",
        help="Allow tracts to be truncated and re-tracked due to poor structural "
        f"termination during ACT. [default: "
        f"{cfg_.reconstruction.TractographyACTConfig.backtrack}]",
    ),
    tract_act_nocrop: bool | None = typer.Option(
        None,
        "--tractography-act-nocrop",
        help="Do not crop streamline endpoints as they cross the GM-WM interface. "
        f"[default: {cfg_.reconstruction.TractographyACTConfig.no_crop_gmwmi}]",
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="Verbosity (-v, -vv, -vvv)."),
) -> None:
    """Reconstruction stage-level."""
    local_vars = locals()
    builder = partial(
        cfg_.utils.build_config, ctx_params=ctx.params, cfg_file=opts_config
    )
    mapper = partial(cfg_.utils.map_param, vars_dict=local_vars)
    # Global options
    ctx.obj.cfg.opts = cli_utils.build_global_opts(
        ctx_params=ctx.params, cfg_file=opts_config
    )
    # Reconstruction options
    recon_map = {**mapper("query_", "query."), **mapper("tract_", "tractography.")}
    recon_map.update({k: v.replace(".act_", ".opts.") for k, v in recon_map.items()})
    ctx.obj.cfg.reconstruction = builder(
        cfg_class=cfg_.reconstruction.ReconstructionConfig,
        cfg_key="reconstruction",
        include_only=list(recon_map.keys()),
        cli_map=recon_map,
    )
    # Verbosity
    ctx.obj.log_level = cli_utils.setup_logging(verbose)
    # Setup styx
    logger, runner = app.initialize(
        output_dir=ctx.obj.cfg.output_dir, global_opts=ctx.obj.cfg.opts
    )
    cli_utils.finalize_stage(ctx=ctx.obj, logger=logger)
    app.analysis_levels.reconstruction(
        input_dir=ctx.obj.cfg.input_dir,
        output_dir=ctx.obj.cfg.output_dir,
        recon_opts=ctx.obj.cfg.reconstruction,
        global_opts=ctx.obj.cfg.opts,
        runner=runner,
        logger=logger,
    )
