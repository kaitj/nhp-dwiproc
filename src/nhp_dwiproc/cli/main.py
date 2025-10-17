"""Main CLI using callback pattern."""

import logging
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import typer
from niwrap_helper.styx import setup_styx

from .. import app as app
from .. import config as cfg_
from . import utils as cli_utils

LOG_LEVELS = [logging.INFO, logging.DEBUG]

app_ = typer.Typer(
    name="NHP-DWIProc",
    add_completion=False,
    help="Diffusion MRI processing workflows.",
    pretty_exceptions_enable=False,  # Disable typer's rich-formatted traceback
)


@app_.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    # Required
    input_dir: Path = typer.Argument(
        None, exists=True, file_okay=False, readable=True, help="Input directory."
    ),
    output_dir: Path = typer.Argument(
        None, file_okay=False, writable=True, help="Output directory."
    ),
    # Options
    version: bool = typer.Option(
        False,
        "--version",
        help="Show application version and exit.",
        is_eager=True,
    ),
) -> None:
    """Diffusion MRI processing pipeline."""
    # Print version
    if version:
        typer.echo(f"{ctx.info_name.replace('_', '-')} version: {app.version}")
        exit(0)
    # Print help if required args are missing
    if not input_dir and not output_dir or ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
    ctx.obj = SimpleNamespace(
        app=ctx.info_name,
        version=app.version,
        cfg=SimpleNamespace(
            input_dir=input_dir,
            output_dir=output_dir,
            stage=ctx.invoked_subcommand,
        ),
    )


@app_.command(help="Indexing stage.")
def index(
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
        help=f"Number of threads to use [default: {cfg_.GlobalOptsConfig.threads}].",
    ),
    opts_index_path: Path | None = typer.Option(
        None,
        "--index-path",
        help="Path to read / write bids2table index. [default: "
        f"{cfg_.GlobalOptsConfig.index_path}]",
        writable=True,
    ),
    overwrite: bool | None = typer.Option(
        None,
        "--overwrite",
        help="Overwrite existing bids2table index. [default: "
        f"{cfg_.IndexConfig.overwrite}]",
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="Verbosity (-v, -vv, -vvv)."),
) -> None:
    """Index stage-level."""
    builder = partial(
        cfg_.utils.build_config, ctx_params=ctx.params, cfg_file=opts_config
    )
    # Global options
    opt_map = cfg_.utils.map_param("opts_", "", locals())
    ctx.obj.cfg.opt = builder(
        cfg_class=cfg_.GlobalOptsConfig,
        cfg_key="opts",
        include_only=list(opt_map.keys()),
        cli_map=opt_map,
    )
    # Index options
    ctx.obj.cfg.index = builder(
        cfg_class=cfg_.IndexConfig, cfg_key="index", include_only=["overwrite"]
    )
    # Verbosity
    ctx.obj.log_level = (
        LOG_LEVELS[min(verbose, len(LOG_LEVELS)) - 1]
        if verbose > 0
        else logging.CRITICAL + 1
    )
    # Setup styx
    logger, runner = setup_styx(runner="local")
    logger.setLevel(ctx.obj.log_level)
    logger.debug(f"Stage options:\n\n{cli_utils._namespace_to_yaml(obj=ctx.obj)}")
    # Run
    app.analysis_levels.index(
        input_dir=ctx.obj.cfg.input_dir,
        index_opts=ctx.obj.cfg.index,
        global_opts=ctx.obj.cfg.opt,
        runner=runner,
        logger=logger,
    )


@app_.command(help="Processing stage.")
def preprocess(
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
        help="Path to read bids2table index. [default: "
        f"{cfg_.GlobalOptsConfig.index_path}]",
        exists=True,
        resolve_path=True,
    ),
    opts_runner: cfg_.shared.Runner | None = typer.Option(
        None,
        "--runner",
        help=f"Type of runner to run workflow. [default: '{cfg_.RunnerConfig.name}']",
    ),
    opts_images: str | None = typer.Option(
        None,
        "--runner-images",
        callback=cli_utils._json_dict_callback,
        help="JSON string mapping containers to paths for non-local runners. "
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
    opts_b0_thresh: int | None = typer.Option(
        None,
        "--b0-thresh",
        help=f"Threshold for shell to be considered b0. [default: "
        f"{cfg_.GlobalOptsConfig.b0_thresh}]",
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
    query_fmap: str | None = typer.Option(
        None,
        "--fmap-query",
        help="String query for fieldmap-associated BIDS entities. [default: "
        f"{cfg_.QueryConfig.fmap}]",
    ),
    metadata_pe_dirs: list[str] | None = typer.Option(
        None,
        "--pe-dirs",
        help="Set phase encoding for dwi acquisition (space-separated for multiple "
        "acquisitions) overwriting value provided in metadata (JSON) file. "
        f"[default: {cfg_.preprocess.MetadataConfig.pe_dirs}]",
    ),
    metadata_echo_spacing: float = typer.Option(
        None,
        "--echo-spacing",
        help="Estimated echo spacing for dwi acquisitions, value in metadata "
        "(JSON) file will take priority. [default: "
        f"{cfg_.preprocess.MetadataConfig.echo_spacing}]",
    ),
    denoise_skip: bool = typer.Option(
        False,
        "--denoise-skip",
        help=f"Skip denoising step. [default: {cfg_.preprocess.DenoiseConfig.skip}]",
    ),
    denoise_map_: bool = typer.Option(
        False,
        "--denoise-map",
        help=f"Output noise map. [default: {cfg_.preprocess.DenoiseConfig.map_}]",
    ),
    denoise_estimator: cfg_.preprocess.DenoiseEstimator = typer.Option(
        "Exp2",
        "--denoise-estimator",
        help="Noise level estimator. [default: "
        f"{cfg_.preprocess.DenoiseConfig.estimator}]",
    ),
    unring_skip: bool | None = typer.Option(
        None,
        "--unring-skip",
        help=f"Skip unringing step. [default: {cfg_.preprocess.UnringConfig.skip}]",
    ),
    unring_axes: list[int] | None = typer.Option(
        None,
        "--unring-axes",
        help="Slice axes for unringing [default: (0,1 - i.e. x-y)]",
    ),
    undistort_method: cfg_.preprocess.UndistortionMethod | None = typer.Option(
        None,
        "--undistort-method",
        help=f"Distortion correction method - topup performed unless skipped or using "
        f"'eddymotion'. [default: '{cfg_.preprocess.UndistortionConfig.method}']",
    ),
    topup_skip: bool | None = typer.Option(
        None,
        "--topup-skip",
        help=f"Skip TOPUP step. [default: {cfg_.preprocess.TopupConfig.skip}]",
    ),
    topup_config: str | None = typer.Option(
        None,
        "--topup-method",
        help="TOPUP configuration file; custom path "
        "can be provided or choose from: 'b02b0', 'b02b0_macaque', "
        f"'b02b0_marmoset' [default: '{cfg_.preprocess.TopupConfig.config}']",
    ),
    eddy_skip: bool | None = typer.Option(
        None,
        "--eddy-skip",
        help=f"Skip Eddy step. [default: {cfg_.preprocess.EddyConfig.skip}]",
    ),
    eddy_slm: cfg_.preprocess.EddySLMModel | None = typer.Option(
        None,
        "--eddy-slm",
        help="Diffusion gradient model for generating eddy currents in Eddy step. "
        f"[default: {cfg_.preprocess.EddyConfig.slm}]",
    ),
    eddy_cnr: bool | None = typer.Option(
        None,
        "--eddy-cnr",
        help="Generate CNR maps in Eddy step. [default: "
        f"{cfg_.preprocess.EddyConfig.cnr}]",
    ),
    eddy_repol: bool | None = typer.Option(
        None,
        "--eddy-repol",
        help="Replace outliers in Eddy step. [default: "
        f"{cfg_.preprocess.EddyConfig.repol}]",
    ),
    eddy_residuals: bool | None = typer.Option(
        None,
        "--eddy-residuals",
        help="Generate 4D residual volume. [default: "
        f"{cfg_.preprocess.EddyConfig.residuals}]",
    ),
    eddy_shelled: bool | None = typer.Option(
        None,
        "--eddy-shelled",
        help="Indicate diffusion data is shelled, skipping checking during Eddy. "
        f"[default: {cfg_.preprocess.EddyConfig.shelled}]",
    ),
    eddymotion_skip: bool | None = typer.Option(
        None,
        "--eddymotion-skip",
        help=f"Skip Eddymotion step. [default: {cfg_.preprocess.EddyConfig.skip}]",
    ),
    eddymotion_iters: int | None = typer.Option(
        None,
        "--eddymotion-iters",
        help=f"Number of iterations for eddymotion. [default: "
        f"{cfg_.preprocess.EddyMotionConfig.iters}]",
    ),
    fugue_skip: bool | None = typer.Option(
        None,
        "--fugue-skip",
        help="Skip legacy FSL fugue step. [default: "
        f"{cfg_.preprocess.FugueConfig.skip}]",
    ),
    fugue_smooth: bool | None = typer.Option(
        None,
        "--fugue-smooth",
        help="3D Gaussian smoothing sigma (in mm). [default: "
        f"{cfg_.preprocess.FugueConfig.skip}]",
    ),
    bias_skip: bool | None = typer.Option(
        None,
        "--biascorrect-skip",
        help="Skip biascorrection step. [default: "
        f"{cfg_.preprocess.BiascorrectConfig.skip}]",
    ),
    bias_spacing: float | None = typer.Option(
        None,
        "--biascorrect-spacing",
        help=f"Initial biascorrection mesh resolution in mm. [default: "
        f"{cfg_.preprocess.BiascorrectConfig.spacing}]",
    ),
    bias_iters: int | None = typer.Option(
        None,
        "--biascorrect-iters",
        help=f"Number of biascorrection iterations. [default: "
        f"{cfg_.preprocess.BiascorrectConfig.iters}]",
    ),
    bias_shrink: int | None = typer.Option(
        None,
        "--biascorrect-shrink",
        help=f"Biascorrection shrink factor applied to spatial dimension. [default: "
        f"{cfg_.preprocess.BiascorrectConfig.shrink}]",
    ),
    reg_skip: bool | None = typer.Option(
        None,
        "--register-skip",
        help=f"Skip registration step to participant anatomical. [default: "
        f"{cfg_.preprocess.RegistrationConfig.skip}]",
    ),
    reg_metric: cfg_.preprocess.RegistrationMetric | None = typer.Option(
        None,
        "--register-metric",
        help=f"Similarity metric to use for registration step. [default: "
        f"'{cfg_.preprocess.RegistrationConfig.metric}']",
    ),
    reg_iters: str | None = typer.Option(
        None,
        "--register-iters",
        help="Number of iterations per level of multi-res in registration step. "
        f"[default: {cfg_.preprocess.RegistrationConfig.iters}]",
    ),
    reg_init: cfg_.preprocess.RegistrationInit | None = typer.Option(
        None,
        "--register-init",
        help="Initialization method for registration step. [default: "
        f"'{cfg_.preprocess.RegistrationConfig.init}']",
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="Verbosity (-v, -vv, -vvv)."),
) -> None:
    """Preprocess stage-level."""
    builder = partial(
        cfg_.utils.build_config, ctx_params=ctx.params, cfg_file=opts_config
    )
    mapper = partial(cfg_.utils.map_param, vars_dict=locals())
    # Global options
    opt_map = mapper("opts_", "")
    opt_map.update({"opts_runner": "runner.name", "opts_images": "runner.images"})
    ctx.obj.cfg.opts = builder(
        cfg_class=cfg_.GlobalOptsConfig,
        cfg_key="opts",
        include_only=list(opt_map.keys()),
        cli_map=opt_map,
    )
    # Preprocess options
    preproc_map = {
        **mapper("query_", "query."),
        **mapper("metadata_", "metadata."),
        **mapper("denoise_", "denoise."),
        **mapper("unring_", "unring."),
        **{"undistort_method": "undistort.method"},
        **mapper("topup_", "undistort.opts.topup."),
        **mapper("eddy_", "undistort.opts.eddy."),
        **mapper("eddymotion_", "undistort.opts.eddymotion."),
        **mapper("fugue_", "undistort.opts.fugue"),
        **mapper("bias_", "biascorrect."),
        **mapper("reg_", "registration."),
    }
    ctx.obj.cfg.preprocess = builder(
        cfg_class=cfg_.preprocess.PreprocessConfig,
        cfg_key="preprocess",
        include_only=list(preproc_map.keys()),
        cli_map=preproc_map,
    )
    # Post config initialization
    match ctx.obj.cfg.preprocess.undistort.method:
        case "eddymotion":
            ctx.obj.cfg.preprocess.undistort.opts.topup = None
            ctx.obj.cfg.preprocess.undistort.opts.eddy = None
            ctx.obj.cfg.preprocess.undistort.opts.fugue = None
        case "fugue":
            ctx.obj.cfg.preprocess.undistort.opts.topup = None
            ctx.obj.cfg.preprocess.undistort.opts.eddy = None
            ctx.obj.cfg.preprocess.undistort.opts.eddymotion = None
        case _:
            ctx.obj.cfg.preprocess.undistort.opts.eddymotion = None
            ctx.obj.cfg.preprocess.undistort.opts.fugue = None
    # Verbosity
    ctx.obj.log_level = (
        LOG_LEVELS[min(verbose, len(LOG_LEVELS)) - 1]
        if verbose > 0
        else logging.CRITICAL + 1
    )
    # Setup styx
    logger, runner = app.initialize(
        output_dir=ctx.obj.cfg.output_dir, global_opts=ctx.obj.cfg.opts
    )
    logger.setLevel(ctx.obj.log_level)
    logger.debug(f"Stage options:\n\n{cli_utils._namespace_to_yaml(obj=ctx.obj)}")
    # Run
    cfg_.utils.generate_descriptor(
        app_name=ctx.obj.app,
        version=ctx.obj.app,
        out_fpath=ctx.obj.cfg.output_dir / "dataset_description.json",
    )
    app.analysis_levels.preprocess(
        input_dir=ctx.obj.cfg.input_dir,
        output_dir=ctx.obj.cfg.output_dir,
        preproc_opts=ctx.obj.cfg.preprocess,
        global_opts=ctx.obj.cfg.opts,
        runner=runner,
        logger=logger,
    )


@app_.command(help="Reconstruction stage.")
def reconstruction(
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
        callback=cli_utils._json_dict_callback,
        help="JSON string mapping containers to paths for non-local runners. "
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
        help="Space-separated list of b-values (b0 must be explicitly included). "
        f"[default: {cfg_.reconstruction.TractographyConfig.shells}]",
    ),
    tract_lmax: list[int] | None = typer.Option(
        None,
        "--lmax",
        help="Space-separated list of maximum harmonic degrees (b0 must be explicitly "
        f"included). [default: {cfg_.reconstruction.TractographyConfig.lmax}]",
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
    opt_map = mapper("opts_", "")
    opt_map.update({"opts_runner": "runner.name", "opts_images": "runner.images"})
    ctx.obj.cfg.opts = builder(
        cfg_class=cfg_.GlobalOptsConfig,
        cfg_key="opts",
        include_only=list(opt_map.keys()),
        cli_map=opt_map,
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
    ctx.obj.log_level = (
        LOG_LEVELS[min(verbose, len(LOG_LEVELS)) - 1]
        if verbose > 0
        else logging.CRITICAL + 1
    )
    # Setup styx
    logger, runner = app.initialize(
        output_dir=ctx.obj.cfg.output_dir, global_opts=ctx.obj.cfg.opts
    )
    logger.setLevel(ctx.obj.log_level)
    logger.debug(f"Stage options:\n\n{cli_utils._namespace_to_yaml(obj=ctx.obj)}")
    # Run
    cfg_.utils.generate_descriptor(
        app_name=ctx.obj.app,
        version=ctx.obj.app,
        out_fpath=ctx.obj.cfg.output_dir / "dataset_description.json",
    )
    app.analysis_levels.reconstruction(
        input_dir=ctx.obj.cfg.input_dir,
        output_dir=ctx.obj.cfg.output_dir,
        recon_opts=ctx.obj.cfg.reconstruction,
        global_opts=ctx.obj.cfg.opts,
        runner=runner,
        logger=logger,
    )


@app_.command(help="Connectivity stage.")
def connectivity(
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
        callback=cli_utils._json_dict_callback,
        help="JSON string mapping containers to paths for non-local runners. "
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
    opt_map = mapper("opts_", "")
    opt_map.update({"opts_runner": "runner.name", "opts_images": "runner.images"})
    ctx.obj.cfg.opts = builder(
        cfg_class=cfg_.GlobalOptsConfig,
        cfg_key="opts",
        include_only=list(opt_map.keys()),
        cli_map=opt_map,
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
    ctx.obj.log_level = (
        LOG_LEVELS[min(verbose, len(LOG_LEVELS)) - 1]
        if verbose > 0
        else logging.CRITICAL + 1
    )
    # Setup styx
    logger, runner = app.initialize(
        output_dir=ctx.obj.cfg.output_dir, global_opts=ctx.obj.cfg.opts
    )
    logger.setLevel(ctx.obj.log_level)
    logger.debug(f"Stage options:\n\n{cli_utils._namespace_to_yaml(obj=ctx.obj)}")
    # Run
    cfg_.utils.generate_descriptor(
        app_name=ctx.obj.app,
        version=ctx.obj.app,
        out_fpath=ctx.obj.cfg.output_dir / "dataset_description.json",
    )
    app.analysis_levels.connectivity(
        input_dir=ctx.obj.cfg.input_dir,
        output_dir=ctx.obj.cfg.output_dir,
        conn_opts=ctx.obj.cfg.connectivity,
        global_opts=ctx.obj.cfg.opts,
        runner=runner,
        logger=logger,
    )


if __name__ == "__main__":
    app_()
