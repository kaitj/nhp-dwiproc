"""Preprocess stage command implementation."""

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
        help="Set phase encoding for dwi acquisition overwriting value provided in "
        "metadata (JSON) file; invoke multiple times for multiple directions)."
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
        show_default=False,
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
        "--topup-config",
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
        f"{cfg_.preprocess.FugueConfig.smooth}]",
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
    ctx.obj.cfg.opts = cli_utils.build_global_opts(
        ctx_params=ctx.params, cfg_file=opts_config
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
    ctx.obj.log_level = cli_utils.setup_logging(verbose)
    # Setup stage
    logger, runner = app.initialize(
        output_dir=ctx.obj.cfg.output_dir, global_opts=ctx.obj.cfg.opts
    )
    cli_utils.finalize_stage(ctx=ctx.obj, logger=logger)
    app.analysis_levels.preprocess(
        input_dir=ctx.obj.cfg.input_dir,
        output_dir=ctx.obj.cfg.output_dir,
        preproc_opts=ctx.obj.cfg.preprocess,
        global_opts=ctx.obj.cfg.opts,
        runner=runner,
        logger=logger,
    )
