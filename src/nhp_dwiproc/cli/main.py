"""Main CLI using callback pattern."""

import json
from pathlib import Path
from types import SimpleNamespace

import typer

from .config import connectivity as conn
from .config import preprocess as preproc
from .config import reconstruction as recon
from .config.shared import GlobalConfig, QueryConfig, Runner, RunnerConfig

app = typer.Typer(
    add_completion=False,
    help="Diffusion MRI processing workflows.",
)


@app.callback()
def main(
    ctx: typer.Context,
    # Required args
    input_dir: Path = typer.Argument(
        ..., exists=True, file_okay=False, readable=True, help="Input directory."
    ),
    output_dir: Path = typer.Argument(
        ..., file_okay=False, writable=True, help="Output directory."
    ),
) -> None:
    """Diffusion MRI processing pipeline."""
    ctx.obj = SimpleNamespace(
        input_dir=input_dir,
        output_dir=output_dir,
    )


@app.command(help="Indexing stage.")
def index(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None, "--config", help="YAML-formatted configuration file."
    ),
    threads: int = typer.Option(1, "--threads", help="Number of threads to use."),
    index_path: Path = typer.Option(
        None, "--index-path", help="Path to read / write bids2table index."
    ),
    overwrite: bool = typer.Option(
        False, "--index-overwrite", help="Overwrite existing bids2table index."
    ),
) -> None:
    """Index stage-level."""
    ctx.obj.opts = GlobalConfig(
        config=config,
        threads=threads,
        index_path=index_path,
    )
    ctx.obj.overwrite = overwrite


@app.command(help="Processing stage.")
def preprocess(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None, "--config", help="YAML-formatted configuration file."
    ),
    threads: int = typer.Option(1, "--threads", help="Number of threads to use."),
    index_path: Path = typer.Option(
        None, "--index-path", help="Path to read / write bids2table index."
    ),
    runner: Runner = typer.Option(
        "local", "--runner", help="Type of runner to run workflow."
    ),
    images: str = typer.Option(
        None,
        "--runner-images",
        help="JSON string mapping containers to paths for non-local runners.",
    ),
    graph: bool = typer.Option(
        False, "--graph", help="Print mermaid diagram of workflow."
    ),
    seed_number: int = typer.Option(
        99, "--seed-num", help="Fixed seed to use for generating reproducible results."
    ),
    work_dir: Path = typer.Option(
        Path("styx_tmp"), "--work-dir", help="Working directory."
    ),
    work_keep: bool = typer.Option(
        False, "--work-keep", help="Keep working directory."
    ),
    b0_thresh: int = typer.Option(
        10, "--b0-thresh", help="Threshold for shell to be considered b0."
    ),
    participant: str = typer.Option(
        None, "--participant-query", help="String query for 'subject' & 'session'."
    ),
    dwi: str = typer.Option(
        None, "--dwi-query", help="String query for DWI-associated BIDS entities."
    ),
    t1w: str = typer.Option(
        None, "--t1w-query", help="String query for T1w-associated BIDS entities."
    ),
    mask: str = typer.Option(
        None,
        "--mask-query",
        help="String query for custom mask -associated BIDS entities.",
    ),
    fmap: str = typer.Option(
        None, "--fmap-query", help="String query for fieldmap-associated BIDS entities."
    ),
    pe_dirs: list[str] = typer.Option(
        None,
        "--pe-dirs",
        help="Set phase encoding for dwi acquisition (space-separated for multiple "
        "acquisitions) overwriting value provided in metadata (JSON) file.",
    ),
    echo_spacing: float = typer.Option(
        None,
        "--echo-spacing",
        help="Estimated echo spacing for all dwi acquisitions, value in metadata "
        "(JSON) file will take priority.",
    ),
    denoise_skip: bool = typer.Option(
        False, "--denoise-skip", help="Skip denoising step."
    ),
    denoise_map: bool = typer.Option(False, "--denoise-map", help="Output noise map."),
    denoise_estimator: preproc.DenoiseEstimator = typer.Option(
        "Exp2", "--denoise-estimator", help="Noise level estimator."
    ),
    unring_skip: bool = typer.Option(
        False, "--unring-skip", help="Skip unringing step."
    ),
    unring_axes: list[int] = typer.Option(
        [0, 1],
        "--unring-axes",
        help="Slice axes for unringing",
    ),
    undistort_method: preproc.DistortionMethod = typer.Option(
        "topup", "--undistort-method", help="Distortion correction method."
    ),
    topup_skip: bool = typer.Option(False, "--topup-skip", help="Skip TOPUP step."),
    topup_config: str = typer.Option(
        "b02b0_macaque",
        "--topup-method",
        help="TOPUP configuration file; custom path "
        "can be provided or choose the following: 'b02b0', 'b02b0_macaque', "
        "'b02b0_marmoset'",
    ),
    eddy_skip: bool = typer.Option(False, "--eddy-skip", help="Skip Eddy step."),
    eddy_slm: preproc.EddySLMModel = typer.Option(
        None,
        "--eddy-slm",
        help="Diffusion gradient model for generating eddy currents during Eddy step.",
    ),
    eddy_cnr: bool = typer.Option(
        False, "--eddy-cnr", help="Generate CNR maps during Eddy step."
    ),
    eddy_repol: bool = typer.Option(
        False, "--eddy-repol", help="Replace outliers during Eddy step."
    ),
    eddy_residuals: bool = typer.Option(
        False, "--eddy-residuals", help="Generate 4D residual volume."
    ),
    eddy_shelled: bool = typer.Option(
        False,
        "--eddy-shelled",
        help="Indicate diffusion data is shelled, skipping checking during Eddy.",
    ),
    eddymotion_iters: int = typer.Option(
        2, "--eddymotion-iters", help="Number of iterations for eddymotion."
    ),
    bias_skip: bool = typer.Option(
        False, "--biascorrect-skip", help="Skip biascorrection step."
    ),
    bias_spacing: float = typer.Option(
        100.00,
        "--biascorrect-spacing",
        help="Initial biascorrection mesh resolution in mm.",
    ),
    bias_iters: int = typer.Option(
        1000, "--biascorrect-iters", help="Number of biascorrection iterations."
    ),
    bias_shrink: int = typer.Option(
        4,
        "--biascorrect-shrink",
        help="Biascorrection shrink factor applied to spatial dimension.",
    ),
    reg_skip: bool = typer.Option(
        False,
        "--register-skip",
        help="Skip registration step to participant anatomical.",
    ),
    reg_metric: preproc.RegistrationMetric = typer.Option(
        "NMI",
        "--register-metric",
        help="Similarity metric to use for registration step.",
    ),
    reg_iters: str = typer.Option(
        "50x50",
        "--register-iters",
        help="Number of iterations per level of multi-res in registration step.",
    ),
    reg_init: preproc.RegistrationInit = typer.Option(
        "identity",
        "--register-init",
        help="Initialization method for registration step.",
    ),
) -> None:
    """Preprocess stage-level."""
    ctx.obj.opts = GlobalConfig(
        config=config,
        threads=threads,
        index_path=index_path,
        runner=RunnerConfig(
            type_=runner, images=json.loads(images) if images is not None else None
        ),
        graph=graph,
        seed_number=seed_number,
        work_dir=work_dir,
        work_keep=work_keep,
        b0_thresh=b0_thresh,
    )
    ctx.obj.query = QueryConfig(
        participant=participant, dwi=dwi, t1w=t1w, mask=mask, fmap=fmap
    )
    ctx.obj.preproc = SimpleNamespace(
        metadata=preproc.MetadataConfig(pe_dirs=pe_dirs, echo_spacing=echo_spacing),
        denoise=preproc.DenoiseConfig(
            skip=denoise_skip, map_=denoise_map, estimator=denoise_estimator
        ),
        unring=preproc.UnringConfig(skip=unring_skip, axes=unring_axes),
        undistort=SimpleNamespace(
            method=undistort_method,
            opts=SimpleNamespace(
                topup=preproc.TopupConfig(skip=topup_skip, config=topup_config),
                eddy=preproc.EddyConfig(
                    skip=eddy_skip,
                    slm=eddy_slm,
                    cnr=eddy_cnr,
                    repol=eddy_repol,
                    residuals=eddy_residuals,
                    shelled=eddy_shelled,
                ),
            )
            if undistort_method != preproc.DistortionMethod.eddymotion
            else preproc.EddyMotionConfig(iters=eddymotion_iters),
        ),
        biascorrect=preproc.BiascorrectConfig(
            skip=bias_skip, spacing=bias_spacing, iters=bias_iters, shrink=bias_shrink
        ),
        registration=preproc.RegistrationConfig(
            skip=reg_skip, metric=reg_metric, iters=reg_iters, init=reg_init
        ),
    )

    from pprint import pprint

    pprint(ctx.obj)


@app.command(help="Reconstruction stage.")
def reconstruction(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None, "--config", help="YAML-formatted configuration file."
    ),
    threads: int = typer.Option(1, "--threads", help="Number of threads to use."),
    index_path: Path = typer.Option(
        None, "--index-path", help="Path to read / write bids2table index."
    ),
    runner: Runner = typer.Option(
        "local", "--runner", help="Type of runner to run workflow."
    ),
    images: str = typer.Option(
        None,
        "--runner-images",
        help="JSON string mapping containers to paths for non-local runners.",
    ),
    graph: bool = typer.Option(
        False, "--graph", help="Print mermaid diagram of workflow."
    ),
    seed_number: int = typer.Option(
        99, "--seed-num", help="Fixed seed to use for generating reproducible results."
    ),
    work_dir: Path = typer.Option(
        Path("styx_tmp"), "--work-dir", help="Working directory."
    ),
    work_keep: bool = typer.Option(
        False, "--work-keep", help="Keep working directory."
    ),
    b0_thresh: int = typer.Option(
        10, "--b0-thresh", help="Threshold for shell to be considered b0."
    ),
    participant: str = typer.Option(
        None, "--participant-query", help="String query for 'subject' & 'session'."
    ),
    dwi: str = typer.Option(
        None, "--dwi-query", help="String query for DWI-associated BIDS entities."
    ),
    t1w: str = typer.Option(
        None, "--t1w-query", help="String query for T1w-associated BIDS entities."
    ),
    mask: str = typer.Option(
        None,
        "--mask-query",
        help="String query for custom mask -associated BIDS entities.",
    ),
    single_shell: bool = typer.Option(
        False, "--single-shell", help="Indicate single-shell data."
    ),
    shells: list[int] = typer.Option(
        None,
        "--shells",
        help="Space-separated list of b-values (b0 must be explicitly included).",
    ),
    lmax: list[int] = typer.Option(
        None,
        "--lmax",
        help="Space-separated list of maximum harmonic degrees (b0 must be explicitly "
        "included).",
    ),
    steps: float = typer.Option(
        None,
        "--steps",
        help="Step size (in mm) for tractography sampling [default: 0.5 x voxel_size].",
    ),
    cutoff: float = typer.Option(
        0.1, "--cutoff", help="FOD cutoff amplitude for track termination."
    ),
    streamlines: int = typer.Option(
        10_000, "--streamlines", help="Number of streamlines to select."
    ),
    method: recon.TractographyMethod = typer.Option(
        "wm", "--tractography-method", help="Tractography seeding method."
    ),
    act_backtrack: bool = typer.Option(
        False,
        "--tractography-act-backtrack",
        help="Allow tracts to be truncated and "
        "re-tracked due to poor structural termination during ACT.",
    ),
    act_nocrop: bool = typer.Option(
        False,
        "--tractography-act-nocrop",
        help="Do not crop streamline endpoints as they cross the GM-WM interface.",
    ),
) -> None:
    """Reconstruction stage-level."""
    ctx.obj.opts = GlobalConfig(
        config=config,
        threads=threads,
        index_path=index_path,
        runner=RunnerConfig(
            type_=runner, images=json.loads(images) if images is not None else None
        ),
        graph=graph,
        seed_number=seed_number,
        work_dir=work_dir,
        work_keep=work_keep,
        b0_thresh=b0_thresh,
    )
    ctx.obj.query = QueryConfig(participant=participant, dwi=dwi, t1w=t1w, mask=mask)
    ctx.obj.recon = SimpleNamespace(
        tractography=recon.TractographyConfig(
            single_shell=single_shell,
            shells=shells,
            lmax=lmax,
            steps=steps,
            method=method,
            opts=recon.TractographyACTConfig(
                backtrack=act_backtrack, no_crop_gmwmi=act_nocrop
            )
            if method == recon.TractographyMethod.act
            else None,
            cutoff=cutoff,
            streamlines=streamlines,
        )
    )


@app.command(help="Connectivity stage.")
def connectivity(
    ctx: typer.Context,
    config: Path | None = typer.Option(
        None, "--config", help="YAML-formatted configuration file."
    ),
    threads: int = typer.Option(1, "--threads", help="Number of threads to use."),
    index_path: Path = typer.Option(
        None, "--index-path", help="Path to read / write bids2table index."
    ),
    runner: Runner = typer.Option(
        "local", "--runner", help="Type of runner to run workflow."
    ),
    images: str = typer.Option(
        None,
        "--runner-images",
        help="JSON string mapping containers to paths for non-local runners.",
    ),
    graph: bool = typer.Option(
        False, "--graph", help="Print mermaid diagram of workflow."
    ),
    seed_number: int = typer.Option(
        99, "--seed-num", help="Fixed seed to use for generating reproducible results."
    ),
    work_dir: Path = typer.Option(
        Path("styx_tmp"), "--work-dir", help="Working directory."
    ),
    work_keep: bool = typer.Option(
        False, "--work-keep", help="Keep working directory."
    ),
    method: conn.ConnectivityMethod = typer.Option(
        "connectome", "--method", help="Type of connectivity analysis to perform."
    ),
    atlas: str = typer.Option(
        None,
        "--atlas",
        help="Volumetric atlas (assumed to be in same space) to compute connectivity "
        "matrix.",
    ),
    radius: float = typer.Option(
        2.0, "--radius", help="Distance (in mm) to nearest parcel"
    ),
    voxel_size: list[float] = typer.Option(
        None,
        "--vox-mm",
        help="Isotropic voxel size (in mm) or space-separated list of voxel sizes "
        "to map tracts to.",
    ),
    tract: str = typer.Option(
        None,
        "--tract-query",
        help="String query for tract-associated BIDS entities; associated ROIs should "
        "contain description entities of 'include', 'exclude', 'stop' for respective "
        "ROIs.",
    ),
    surface: str = typer.Option(
        None,
        "--surf-query",
        help="String query for surface-associated BIDS entities to perform "
        "ribbon-constrained mapping of streamlines; surface type (e.g. white, pial, "
        "etc.) will be automatically identified.",
    ),
) -> None:
    """Connectivity stage-level."""
    ctx.obj.opts = GlobalConfig(
        config=config,
        threads=threads,
        index_path=index_path,
        runner=RunnerConfig(
            type_=runner, images=json.loads(images) if images is not None else None
        ),
        graph=graph,
        seed_number=seed_number,
        work_dir=work_dir,
        work_keep=work_keep,
    )
    ctx.obj.connectivity = conn.ConnectivityConfig(
        method=method,
        opts=conn.ConnectomeConfig(atlas=atlas, radius=radius)
        if method is conn.ConnectivityMethod.connectome
        else conn.TractMapConfig(voxel_size=voxel_size, tract=tract, surface=surface),
    )
    from pprint import pprint

    pprint(ctx.obj)


if __name__ == "__main__":
    app()
