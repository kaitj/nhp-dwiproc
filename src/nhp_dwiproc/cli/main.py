"""Main CLI using callback pattern."""

import logging
from functools import partial
from pathlib import Path
from types import SimpleNamespace

import typer
from niwrap_helper.styx import setup_styx

from .._version import __version__
from ..app import analysis_levels, initialize
from ..config import connectivity as conn
from ..config import preprocess as preproc
from ..config import reconstruction as recon
from ..config import shared, utils
from .utils import _json_dict_callback, _namespace_to_yaml

LOG_LEVELS = [logging.INFO, logging.DEBUG]

app = typer.Typer(
    name="NHP-DWIProc",
    add_completion=False,
    help="Diffusion MRI processing workflows.",
)


@app.callback(invoke_without_command=True)
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
        typer.echo(f"{ctx.info_name.replace('_', '-')} version: {__version__}")
        exit(0)
    # Print help if required args are missing
    if not input_dir and not output_dir or ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
    ctx.obj = SimpleNamespace(
        app=ctx.info_name,
        version=__version__,
        cfg=SimpleNamespace(
            input_dir=input_dir,
            output_dir=output_dir,
            stage=ctx.invoked_subcommand,
        ),
    )


@app.command(help="Indexing stage.")
def index(
    ctx: typer.Context,
    opts_config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML-formatted configuration file. [default: "
        f"{shared.GlobalOptsConfig.config}]",
        exists=True,
        dir_okay=False,
        file_okay=True,
        resolve_path=True,
    ),
    opts_threads: int | None = typer.Option(
        None,
        "--threads",
        help=f"Number of threads to use [default: {shared.GlobalOptsConfig.threads}].",
    ),
    opts_index_path: Path | None = typer.Option(
        None,
        "--index-path",
        help="Path to read / write bids2table index. [default: "
        f"{shared.GlobalOptsConfig.index_path}]",
        writable=True,
    ),
    overwrite: bool | None = typer.Option(
        None,
        "--overwrite",
        help="Overwrite existing bids2table index. [default: "
        f"{shared.IndexConfig.overwrite}]",
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="Verbosity (-v, -vv, -vvv)."),
) -> None:
    """Index stage-level."""
    builder = partial(utils.build_config, ctx_params=ctx.params, cfg_file=opts_config)
    # Global options
    opt_map = utils.map_param("opts_", "", locals())
    ctx.obj.cfg.opt = builder(
        cfg_class=shared.GlobalOptsConfig,
        cfg_key="opts",
        include_only=list(opt_map.keys()),
        cli_map=opt_map,
    )
    # Index options
    ctx.obj.cfg.index = builder(
        cfg_class=shared.IndexConfig, cfg_key="index", include_only=["overwrite"]
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
    logger.debug(f"Stage options:\n\n{_namespace_to_yaml(obj=ctx.obj)}")
    # Run
    analysis_levels.index(
        input_dir=ctx.obj.cfg.input_dir,
        index_opts=ctx.obj.cfg.index,
        global_opts=ctx.obj.cfg.opt,
        runner=runner,
        logger=logger,
    )


@app.command(help="Processing stage.")
def preprocess(
    ctx: typer.Context,
    opts_config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML-formatted configuration file. [default: "
        f"{shared.GlobalOptsConfig.config}]",
        exists=True,
        dir_okay=False,
        file_okay=True,
        resolve_path=True,
    ),
    opts_threads: int | None = typer.Option(
        None,
        "--threads",
        help=f"Number of threads to use. [default: {shared.GlobalOptsConfig.threads}]",
    ),
    opts_index_path: Path | None = typer.Option(
        None,
        "--index-path",
        help="Path to read bids2table index. [default: "
        f"{shared.GlobalOptsConfig.index_path}]",
        exists=True,
        resolve_path=True,
    ),
    opts_runner: shared.Runner | None = typer.Option(
        None,
        "--runner",
        help=f"Type of runner to run workflow. [default: '{shared.RunnerConfig.name}']",
    ),
    opts_images: str | None = typer.Option(
        None,
        "--runner-images",
        callback=_json_dict_callback,
        help="JSON string mapping containers to paths for non-local runners. "
        f"[default: {shared.RunnerConfig.images}]",
    ),
    opts_graph: bool | None = typer.Option(
        None,
        "--graph",
        help="Print mermaid diagram of workflow. [default: "
        f"{shared.GlobalOptsConfig.graph}]",
    ),
    opts_seed_number: int | None = typer.Option(
        None,
        "--seed-num",
        help="Fixed seed to use for generating reproducible results. [default: "
        f"{shared.GlobalOptsConfig.seed_number}]",
    ),
    opts_work_dir: Path | None = typer.Option(
        None,
        "--work-dir",
        help=f"Working directory. [default: '{shared.GlobalOptsConfig.work_dir}']",
        file_okay=False,
        resolve_path=True,
    ),
    opts_work_keep: bool | None = typer.Option(
        None,
        "--work-keep",
        help=f"Keep working directory. [default: {shared.GlobalOptsConfig.work_keep}]",
    ),
    opts_b0_thresh: int | None = typer.Option(
        None,
        "--b0-thresh",
        help=f"Threshold for shell to be considered b0. [default: "
        f"{shared.GlobalOptsConfig.b0_thresh}]",
    ),
    query_participant: str | None = typer.Option(
        None,
        "--participant-query",
        help="String query for 'subject' & 'session'. [default: "
        f"{shared.QueryConfig.participant}]",
    ),
    query_dwi: str | None = typer.Option(
        None,
        "--dwi-query",
        help="String query for DWI-associated BIDS entities. [default: "
        f"{shared.QueryConfig.dwi}]",
    ),
    query_t1w: str | None = typer.Option(
        None,
        "--t1w-query",
        help="String query for T1w-associated BIDS entities. [default: "
        f"{shared.QueryConfig.t1w}]",
    ),
    query_mask: str | None = typer.Option(
        None,
        "--mask-query",
        help="String query for custom mask-associated BIDS entities. [default: "
        f"{shared.QueryConfig.mask}]",
    ),
    query_fmap: str | None = typer.Option(
        None,
        "--fmap-query",
        help="String query for fieldmap-associated BIDS entities. [default: "
        f"{shared.QueryConfig.fmap}]",
    ),
    metadata_pe_dirs: list[str] | None = typer.Option(
        None,
        "--pe-dirs",
        help="Set phase encoding for dwi acquisition (space-separated for multiple "
        "acquisitions) overwriting value provided in metadata (JSON) file. "
        f"[default: {preproc.MetadataConfig.pe_dirs}]",
    ),
    metadata_echo_spacing: float = typer.Option(
        None,
        "--echo-spacing",
        help="Estimated echo spacing for dwi acquisitions, value in metadata "
        "(JSON) file will take priority. [default: "
        f"{preproc.MetadataConfig.echo_spacing}]",
    ),
    denoise_skip: bool = typer.Option(
        False,
        "--denoise-skip",
        help=f"Skip denoising step. [default: {preproc.DenoiseConfig.skip}]",
    ),
    denoise_map_: bool = typer.Option(
        False,
        "--denoise-map",
        help=f"Output noise map. [default: {preproc.DenoiseConfig.map_}]",
    ),
    denoise_estimator: preproc.DenoiseEstimator = typer.Option(
        "Exp2",
        "--denoise-estimator",
        help=f"Noise level estimator. [default: {preproc.DenoiseConfig.estimator}]",
    ),
    unring_skip: bool | None = typer.Option(
        None,
        "--unring-skip",
        help=f"Skip unringing step. [default: {preproc.UnringConfig.skip}]",
    ),
    unring_axes: list[int] | None = typer.Option(
        None,
        "--unring-axes",
        help=f"Slice axes for unringing [default: {preproc.UnringConfig.axes}]",
    ),
    undistort_method: preproc.UndistortionMethod | None = typer.Option(
        None,
        "--undistort-method",
        help=f"Distortion correction method - topup performed unless skipped or using "
        f"'eddymotion'. [default: '{preproc.UndistortionConfig.method}']",
    ),
    topup_skip: bool | None = typer.Option(
        None,
        "--topup-skip",
        help=f"Skip TOPUP step. [default: {preproc.TopupConfig.skip}]",
    ),
    topup_config: str | None = typer.Option(
        None,
        "--topup-method",
        help="TOPUP configuration file; custom path "
        "can be provided or choose from: 'b02b0', 'b02b0_macaque', "
        f"'b02b0_marmoset' [default: '{preproc.TopupConfig.config}']",
    ),
    eddy_skip: bool | None = typer.Option(
        None,
        "--eddy-skip",
        help=f"Skip Eddy step. [default: {preproc.EddyConfig.skip}]",
    ),
    eddy_slm: preproc.EddySLMModel | None = typer.Option(
        None,
        "--eddy-slm",
        help="Diffusion gradient model for generating eddy currents in Eddy step. "
        f"[default: {preproc.EddyConfig.slm}]",
    ),
    eddy_cnr: bool | None = typer.Option(
        None,
        "--eddy-cnr",
        help=f"Generate CNR maps in Eddy step. [default: {preproc.EddyConfig.cnr}]",
    ),
    eddy_repol: bool | None = typer.Option(
        None,
        "--eddy-repol",
        help=f"Replace outliers in Eddy step. [default: {preproc.EddyConfig.repol}]",
    ),
    eddy_residuals: bool | None = typer.Option(
        None,
        "--eddy-residuals",
        help=f"Generate 4D residual volume. [default: {preproc.EddyConfig.residuals}]",
    ),
    eddy_shelled: bool | None = typer.Option(
        None,
        "--eddy-shelled",
        help="Indicate diffusion data is shelled, skipping checking during Eddy. "
        f"[default: {preproc.EddyConfig.shelled}]",
    ),
    eddymotion_skip: bool | None = typer.Option(
        None,
        "--eddymotion-skip",
        help=f"Skip Eddymotion step. [default: {preproc.EddyConfig.skip}]",
    ),
    eddymotion_iters: int | None = typer.Option(
        None,
        "--eddymotion-iters",
        help=f"Number of iterations for eddymotion. [default: "
        f"{preproc.EddyMotionConfig.iters}]",
    ),
    bias_skip: bool | None = typer.Option(
        None,
        "--biascorrect-skip",
        help=f"Skip biascorrection step. [default: {preproc.BiascorrectConfig.skip}]",
    ),
    bias_spacing: float | None = typer.Option(
        None,
        "--biascorrect-spacing",
        help=f"Initial biascorrection mesh resolution in mm. [default: "
        f"{preproc.BiascorrectConfig.spacing}]",
    ),
    bias_iters: int | None = typer.Option(
        None,
        "--biascorrect-iters",
        help=f"Number of biascorrection iterations. [default: "
        f"{preproc.BiascorrectConfig.iters}]",
    ),
    bias_shrink: int | None = typer.Option(
        None,
        "--biascorrect-shrink",
        help=f"Biascorrection shrink factor applied to spatial dimension. [default: "
        f"{preproc.BiascorrectConfig.shrink}]",
    ),
    reg_skip: bool | None = typer.Option(
        None,
        "--register-skip",
        help=f"Skip registration step to participant anatomical. [default: "
        f"{preproc.RegistrationConfig.skip}]",
    ),
    reg_metric: preproc.RegistrationMetric | None = typer.Option(
        None,
        "--register-metric",
        help=f"Similarity metric to use for registration step. [default: "
        f"'{preproc.RegistrationConfig.metric}']",
    ),
    reg_iters: str | None = typer.Option(
        None,
        "--register-iters",
        help="Number of iterations per level of multi-res in registration step. "
        f"[default: {preproc.RegistrationConfig.iters}]",
    ),
    reg_init: preproc.RegistrationInit | None = typer.Option(
        None,
        "--register-init",
        help="Initialization method for registration step. [default: "
        f"'{preproc.RegistrationConfig.init}']",
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="Verbosity (-v, -vv, -vvv)."),
) -> None:
    """Preprocess stage-level."""
    builder = partial(utils.build_config, ctx_params=ctx.params, cfg_file=opts_config)
    mapper = partial(utils.map_param, vars_dict=locals())
    # Global options
    opt_map = mapper("opts_", "")
    opt_map.update({"opts_runner": "runner.name", "opts_images": "runner.images"})
    ctx.obj.cfg.opts = builder(
        cfg_class=shared.GlobalOptsConfig,
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
        **mapper("bias_", "biascorrect."),
        **mapper("reg_", "registration."),
    }
    ctx.obj.cfg.preprocess = builder(
        cfg_class=preproc.PreprocessConfig,
        cfg_key="preprocess",
        include_only=list(preproc_map.keys()),
        cli_map=preproc_map,
    )
    # Post config initialization
    match ctx.obj.cfg.preprocess.undistort.method:
        case "eddymotion":
            ctx.obj.cfg.preprocess.undistort.opts.topup = None
            ctx.obj.cfg.preprocess.undistort.opts.eddy = None
        case _:
            ctx.obj.cfg.preprocess.undistort.opts.eddymotion = None
    # Verbosity
    ctx.obj.log_level = LOG_LEVELS[min(verbose, len(LOG_LEVELS)) - 1]
    if ctx.obj.log_level <= logging.DEBUG:
        print(_namespace_to_yaml(ctx.obj))


@app.command(help="Reconstruction stage.")
def reconstruction(
    ctx: typer.Context,
    opts_config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML-formatted configuration file. [default: "
        f"{shared.GlobalOptsConfig.config}]",
        exists=True,
        dir_okay=False,
        file_okay=True,
        resolve_path=True,
    ),
    opts_threads: int | None = typer.Option(
        None,
        "--threads",
        help=f"Number of threads to use. [default: {shared.GlobalOptsConfig.threads}]",
    ),
    opts_index_path: Path | None = typer.Option(
        None,
        "--index-path",
        help="Path to read / write bids2table index. [default: "
        f"{shared.GlobalOptsConfig.index_path}]",
    ),
    opts_runner: shared.Runner | None = typer.Option(
        None,
        "--runner",
        help=f"Type of runner to run workflow. [default: '{shared.RunnerConfig.name}']",
    ),
    opts_images: str | None = typer.Option(
        None,
        "--runner-images",
        callback=_json_dict_callback,
        help="JSON string mapping containers to paths for non-local runners. "
        f"[default: {shared.RunnerConfig.images}]",
    ),
    opts_graph: bool | None = typer.Option(
        None,
        "--graph",
        help="Print mermaid diagram of workflow. [default: "
        f"{shared.GlobalOptsConfig.graph}]",
    ),
    opts_seed_number: int | None = typer.Option(
        None,
        "--seed-num",
        help="Fixed seed to use for generating reproducible results. [default: "
        f"{shared.GlobalOptsConfig.seed_number}]",
    ),
    opts_work_dir: Path | None = typer.Option(
        None,
        "--work-dir",
        help=f"Working directory. [default: '{shared.GlobalOptsConfig.work_dir}']",
        file_okay=False,
        resolve_path=True,
    ),
    opts_work_keep: bool | None = typer.Option(
        None,
        "--work-keep",
        help=f"Keep working directory. [default: {shared.GlobalOptsConfig.work_keep}]",
    ),
    query_participant: str | None = typer.Option(
        None,
        "--participant-query",
        help="String query for 'subject' & 'session'. [default: "
        f"{shared.QueryConfig.participant}]",
    ),
    query_dwi: str | None = typer.Option(
        None,
        "--dwi-query",
        help="String query for DWI-associated BIDS entities. [default: "
        f"{shared.QueryConfig.dwi}]",
    ),
    query_t1w: str | None = typer.Option(
        None,
        "--t1w-query",
        help="String query for T1w-associated BIDS entities. [default: "
        f"{shared.QueryConfig.t1w}]",
    ),
    query_mask: str | None = typer.Option(
        None,
        "--mask-query",
        help="String query for custom mask-associated BIDS entities. [default: "
        f"{shared.QueryConfig.mask}]",
    ),
    tract_single_shell: bool | None = typer.Option(
        None,
        "--single-shell",
        help="Indicate single-shell data. [default: "
        f"{recon.TractographyConfig.single_shell}]",
    ),
    tract_shells: list[int] | None = typer.Option(
        None,
        "--shells",
        help="Space-separated list of b-values (b0 must be explicitly included). "
        f"[default: {recon.TractographyConfig.shells}]",
    ),
    tract_lmax: list[int] | None = typer.Option(
        None,
        "--lmax",
        help="Space-separated list of maximum harmonic degrees (b0 must be explicitly "
        f"included). [default: {recon.TractographyConfig.lmax}]",
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
        f"{recon.TractographyConfig.cutoff}]",
    ),
    tract_streamlines: int | None = typer.Option(
        None,
        "--streamlines",
        help="Number of streamlines to select. [default: "
        f"{recon.TractographyConfig.streamlines}]",
    ),
    tract_method: recon.TractographyMethod | None = typer.Option(
        None,
        "--tractography-method",
        help="Tractography seeding method. [default: "
        f"{recon.TractographyConfig.method}]",
    ),
    tract_act_backtrack: bool | None = typer.Option(
        None,
        "--tractography-act-backtrack",
        help="Allow tracts to be truncated and re-tracked due to poor structural "
        f"termination during ACT. [default: {recon.TractographyACTConfig.backtrack}]",
    ),
    tract_act_nocrop: bool | None = typer.Option(
        None,
        "--tractography-act-nocrop",
        help="Do not crop streamline endpoints as they cross the GM-WM interface. "
        f"[default: {recon.TractographyACTConfig.no_crop_gmwmi}]",
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="Verbosity (-v, -vv, -vvv)."),
) -> None:
    """Reconstruction stage-level."""
    local_vars = locals()
    builder = partial(utils.build_config, ctx_params=ctx.params, cfg_file=opts_config)
    mapper = partial(utils.map_param, vars_dict=local_vars)
    # Global options
    opt_map = mapper("opts_", "")
    opt_map.update({"opts_runner": "runner.name", "opts_images": "runner.images"})
    ctx.obj.cfg.opts = builder(
        cfg_class=shared.GlobalOptsConfig,
        cfg_key="opts",
        include_only=list(opt_map.keys()),
        cli_map=opt_map,
    )
    # Reconstruction options
    recon_map = {**mapper("query_", "query."), **mapper("tract_", "tractography.")}
    recon_map.update({k: v.replace(".act_", ".opts.") for k, v in recon_map.items()})
    ctx.obj.cfg.reconstruction = builder(
        cfg_class=recon.ReconstructionConfig,
        cfg_key="reconstruction",
        include_only=list(recon_map.keys()),
        cli_map=recon_map,
    )
    # Verbosity
    ctx.obj.log_level = LOG_LEVELS[min(verbose, len(LOG_LEVELS)) - 1]
    if ctx.obj.log_level <= logging.DEBUG:
        from pprint import pprint

        pprint(ctx.obj)
        # print(_namespace_to_yaml(ctx.obj))


@app.command(help="Connectivity stage.")
def connectivity(
    ctx: typer.Context,
    opts_config: Path | None = typer.Option(
        None,
        "--config",
        help="YAML-formatted configuration file. [default: "
        f"{shared.GlobalOptsConfig.config}]",
        exists=True,
        dir_okay=False,
        file_okay=True,
        resolve_path=True,
    ),
    opts_threads: int | None = typer.Option(
        None,
        "--threads",
        help=f"Number of threads to use. [default: {shared.GlobalOptsConfig.threads}]",
    ),
    opts_index_path: Path | None = typer.Option(
        None,
        "--index-path",
        help="Path to read / write bids2table index. [default: "
        f"{shared.GlobalOptsConfig.index_path}]",
    ),
    opts_runner: shared.Runner | None = typer.Option(
        None,
        "--runner",
        help=f"Type of runner to run workflow. [default: '{shared.RunnerConfig.name}']",
    ),
    opts_images: str | None = typer.Option(
        None,
        "--runner-images",
        callback=_json_dict_callback,
        help="JSON string mapping containers to paths for non-local runners. "
        f"[default: {shared.RunnerConfig.images}]",
    ),
    opts_graph: bool | None = typer.Option(
        None,
        "--graph",
        help="Print mermaid diagram of workflow. [default: "
        f"{shared.GlobalOptsConfig.graph}]",
    ),
    opts_seed_number: int | None = typer.Option(
        None,
        "--seed-num",
        help="Fixed seed to use for generating reproducible results. [default: "
        f"{shared.GlobalOptsConfig.seed_number}]",
    ),
    opts_work_dir: Path | None = typer.Option(
        None,
        "--work-dir",
        help=f"Working directory. [default: '{shared.GlobalOptsConfig.work_dir}']",
        file_okay=False,
        resolve_path=True,
    ),
    opts_work_keep: bool | None = typer.Option(
        None,
        "--work-keep",
        help=f"Keep working directory. [default: {shared.GlobalOptsConfig.work_keep}]",
    ),
    query_participant: str | None = typer.Option(
        None,
        "--participant-query",
        help="String query for 'subject' & 'session'. [default: "
        f"{shared.QueryConfig.participant}]",
    ),
    conn_method: conn.ConnectivityMethod | None = typer.Option(
        None,
        "--method",
        help="Type of connectivity analysis to perform. [default: "
        f"'{conn.ConnectivityConfig.method}']",
    ),
    conn_atlas: str | None = typer.Option(
        None,
        "--atlas",
        help="Volumetric atlas (assumed to be in same space) to compute connectivity "
        f"matrix. [default: {conn.ConnectomeConfig.atlas}]",
    ),
    conn_radius: float | None = typer.Option(
        None,
        "--radius",
        help="Distance (in mm) to nearest parcel. [default: "
        f"{conn.ConnectomeConfig.radius}]",
    ),
    conn_voxel_size: list[float] | None = typer.Option(
        None,
        "--vox-mm",
        help="Isotropic voxel size (in mm) or list of voxel sizes "
        f"(repeat argument) for tract map. [default: {conn.TractMapConfig.voxel_size}]",
    ),
    conn_tract_query: str | None = typer.Option(
        None,
        "--tract-query",
        help="String query for tract-associated BIDS entities; associated ROIs should "
        "contain description entities of 'include', 'exclude', 'stop' for respective "
        f"ROIs. [default: {conn.TractMapConfig.tract_query}]",
    ),
    conn_surface_query: str | None = typer.Option(
        None,
        "--surf-query",
        help="String query for surface-associated BIDS entities to perform "
        "ribbon-constrained mapping of streamlines; surface type (e.g. white, pial, "
        "etc.) will be automatically identified. "
        f"[default: {conn.TractMapConfig.surface_query}]",
    ),
    verbose: int = typer.Option(0, "-v", count=True, help="Verbosity (-v, -vv, -vvv)."),
) -> None:
    """Connectivity stage-level."""
    local_vars = locals()
    builder = partial(utils.build_config, ctx_params=ctx.params, cfg_file=opts_config)
    mapper = partial(utils.map_param, vars_dict=local_vars)
    # Global options
    opt_map = mapper("opts_", "")
    opt_map.update({"opts_runner": "runner.name", "opts_images": "runner.images"})
    ctx.obj.cfg.opts = builder(
        cfg_class=shared.GlobalOptsConfig,
        cfg_key="opts",
        include_only=list(opt_map.keys()),
        cli_map=opt_map,
    )
    # Stage specific options
    conn_map = mapper("conn_", "opts.")
    conn_map.update({"conn_method": "method", "query_participant": "query.participant"})
    method_map: dict[str, dict[object, type]] = {
        "method": {
            "connectome": conn.ConnectomeConfig,
            "tract": conn.TractMapConfig,
        },
    }
    ctx.obj.cfg.connectivity = builder(
        cfg_class=conn.ConnectivityConfig,
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
    logger, runner = initialize(
        output_dir=ctx.obj.cfg.output_dir, global_opts=ctx.obj.cfg.opts
    )
    logger.setLevel(ctx.obj.log_level)
    logger.debug(f"Stage options:\n\n{_namespace_to_yaml(obj=ctx.obj)}")
    # Run
    utils.generate_descriptor(
        app_name=ctx.obj.app,
        version=ctx.obj.app,
        out_fpath=ctx.obj.cfg.output_dir / "dataset_description.json",
    )
    analysis_levels.connectivity(
        input_dir=ctx.obj.cfg.input_dir,
        output_dir=ctx.obj.cfg.output_dir,
        conn_opts=ctx.obj.cfg.connectivity,
        global_opts=ctx.obj.cfg.opts,
        runner=runner,
        logger=logger,
    )


if __name__ == "__main__":
    app()
