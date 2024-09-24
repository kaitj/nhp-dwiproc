"""Application command-line interface."""

import pathlib as pl

from bidsapp_helper.parser import BidsAppArgumentParser

from nhp_dwiproc.app.utils import APP_NAME


def parser() -> BidsAppArgumentParser:
    """Initialize and update parser."""
    app_parser = BidsAppArgumentParser(
        app_name=APP_NAME,
        description="Diffusion processing NHP data.",
    )
    app_parser.update_analysis_level(
        ["index", "preprocess", "tractography", "connectivity"]
    )
    _add_optional_args(app_parser=app_parser)
    _add_index_args(app_parser=app_parser)
    _add_preprocess_args(app_parser=app_parser)
    _add_tractography_args(app_parser=app_parser)
    _add_connectivity_args(app_parser=app_parser)
    return app_parser


def _add_optional_args(app_parser: BidsAppArgumentParser) -> None:
    """General optional arguments."""
    app_parser.add_argument(
        "--runner",
        metavar="runner",
        dest="opt.runner",
        type=str,
        choices=["None", "Docker", "Singularity", "Apptainer"],
        help="workflow runner to use (one of [%(choices)s]; default: %(default)s)",
    )
    app_parser.add_argument(
        "--working-dir",
        "--working_dir",
        metavar="directory",
        dest="opt.working_dir",
        default="styx_tmp",
        type=pl.Path,
        help="working directory to temporarily write to (default: %(default)s)",
    )
    app_parser.add_argument(
        "--container-config",
        "--container_config",
        metavar="config",
        dest="opt.containers",
        default=None,
        type=pl.Path,
        help="YAML config file mapping containers to 'local' paths",
    )
    app_parser.add_argument(
        "--threads",
        metavar="threads",
        dest="opt.threads",
        type=int,
        default=1,
        help="number of threads to use (default: %(default)d)",
    )
    app_parser.add_argument(
        "--keep-tmp",
        "--keep_tmp",
        dest="opt.keep_tmp",
        action="store_true",
        help="keep all intermediate files (for debugging purposes)",
    )
    app_parser.add_argument(
        "--seed-num",
        "--seed_num",
        metavar="seed_num",
        dest="opt.seed_num",
        type=int,
        default=99,
        help="fixed seed for reproducible results (default: %(default)d)",
    )
    app_parser.add_argument(
        "--index-path",
        "--index_path",
        metavar="path",
        dest="opt.index_path",
        type=pl.Path,
        default=None,
        help="bids2table index path (default: {bids_dir}/index.b2t)",
    )
    app_parser.add_argument(
        "--graph",
        dest="opt.graph",
        action="store_true",
        help="print diagram of workflow",
    )
    app_parser.add_argument(
        "--participant-query",
        "--participant_query",
        metavar="query",
        dest="participant.query",
        type=str,
        help="string query with bids entities for specific participants",
    )
    app_parser.add_argument(
        "--dwi-query",
        "--dwi_query",
        metavar="query",
        dest="participant.query_dwi",
        type=str,
        help="""string query for bids entities associated with dwi
        (subject & session is assumed); if not provided,
        assumed to be same as participant-query""",
    )
    app_parser.add_argument(
        "--t1w-query",
        "--t1w_query",
        metavar="query",
        dest="participant.query_t1w",
        default=None,
        type=str,
        help="""string query for bids entities associated with t1w
        (subject & session is assumed); if none provided,
        assumed to be same as participant-query""",
    )
    app_parser.add_argument(
        "--mask-query",
        "--mask_query",
        metavar="query",
        dest="participant.query_mask",
        default=None,
        type=str,
        help="""string query for bids entities associated with custom mask
        (subject & session is assumed); no custom query is assumed""",
    )
    app_parser.add_argument(
        "--fmap-query",
        "--fmap_query",
        metavar="query",
        dest="participant.query_fmap",
        default=None,
        type=str,
        help="""string query for bids entities associated with epi fieldmap
        (subject & session is assumed); no custom query is assumed""",
    )
    app_parser.add_argument(
        "--b0-thresh",
        "--b0_thresh",
        metavar="thresh",
        dest="participant.b0_thresh",
        type=int,
        default=10,
        help="threshold for shell to be considered b=0 (default: %(default)d)",
    )


def _add_index_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with index analysis-level."""
    index_args = app_parser.add_argument_group("index analysis-level options")
    index_args.add_argument(
        "--overwrite",
        dest="index.overwrite",
        action="store_true",
        help="overwrite previous index (default: %(default)s)",
    )


def _add_preprocess_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with preprocessing analysis-level."""
    preprocess_args = app_parser.add_argument_group(
        "preprocessing analysis-level options"
    )
    preprocess_args.add_argument(
        "--pe-dirs",
        "--pe_dirs",
        metavar="direction",
        dest="participant.preprocess.metadata.pe_dirs",
        type=str,
        nargs="*",
        help="""set phase encoding direction for dwi acquisition (space-separated for
        multiple acquisitions), overwriting value provided in metadata (JSON) file
        (default: %(default)s)
        """,
    )
    preprocess_args.add_argument(
        "--echo-spacing",
        "--echo_spacing",
        metavar="spacing",
        dest="participant.preprocess.metadata.echo_spacing",
        type=float,
        default=0.0001,
        help="""estimated echo spacing to use for all dwi acquisitions, value in
        metadata (JSON) file will take priority (default: %(default).4f)""",
    )
    preprocess_args.add_argument(
        "--denoise-skip",
        "--denoise_skip",
        dest="participant.preprocess.denoise.skip",
        action="store_true",
        help="skip denoising step",
    )
    preprocess_args.add_argument(
        "--denoise-extent",
        "--denoise_extent",
        metavar="extent",
        dest="participant.preprocess.denoise.extent",
        nargs="*",
        type=int,
        default=None,
        help="""
        patch size of denoising filter (default: smallest isotropic patch size
        exceeding number of dwi volumes)""",
    )
    preprocess_args.add_argument(
        "--denoise-map",
        "--denoise_map",
        dest="participant.preprocess.denoise.map",
        action="store_true",
        help="output noise map (estimated level 'sigma' in the data)",
    )
    preprocess_args.add_argument(
        "--denoise-estimator",
        "--denoise_estimator",
        metavar="estimator",
        dest="participant.preprocess.denoise.estimator",
        type=str,
        default="Exp2",
        choices=["Exp1", "Exp2"],
        help="noise level estimator (one of [%(choices)s]; default: %(default)s)",
    )
    preprocess_args.add_argument(
        "--unring-skip",
        "--unring_skip",
        dest="participant.preprocess.unring.skip",
        action="store_true",
        help="skip unringing step",
    )
    preprocess_args.add_argument(
        "--unring-axes",
        "--unring_axes",
        metavar="axes",
        dest="participant.preprocess.unring.axes",
        nargs="*",
        type=int,
        default=None,
        help="slice axes (space seperated; default: 0,1 - e.g. x-y)",
    )
    preprocess_args.add_argument(
        "--unring-nshifts",
        "--unring_nshifts",
        metavar="nshifts",
        dest="participant.preprocess.unring.nshifts",
        type=int,
        default=20,
        help="discretization of subpixel spacing (default: %(default)d)",
    )
    preprocess_args.add_argument(
        "--unring-minw",
        "--unring_minw",
        metavar="minw",
        dest="participant.preprocess.unring.minW",
        type=int,
        default=1,
        help="left border of window used for computation",
    )
    preprocess_args.add_argument(
        "--unring-maxw",
        "--unring_maxw",
        metavar="maxw",
        dest="participant.preprocess.unring.maxW",
        type=int,
        default=3,
        help="right border of window used for computation",
    )
    preprocess_args.add_argument(
        "--undistort-method",
        "--undistort_method",
        metavar="method",
        dest="participant.preprocess.undistort.method",
        type=str,
        default="fsl",
        choices=["fsl", "fieldmap", "eddymotion"],
        help="distortion correct method (one of [%(choices)s]; default: %(default)s)",
    )
    preprocess_args.add_argument(
        "--eddymotion-iters",
        "--eddymotion_iters",
        metavar="iterations",
        dest="participant.preprocess.eddymotion.iters",
        type=int,
        default=2,
        help="number of iterations to repeat for eddymotion",
    )
    preprocess_args.add_argument(
        "--topup-skip",
        "--topup_skip",
        dest="participant.preprocess.topup.skip",
        action="store_true",
        help="skip FSL topup step",
    )
    preprocess_args.add_argument(
        "--topup-config",
        "--topup_config",
        metavar="config",
        dest="participant.preprocess.topup.config",
        type=str,
        default="b02b0_macaque",
        help="""topup configuration file; custom-config can
        be provided via path or choose from one of the
        following: [b02b0, b02b0_macaque, b02b0_marmoset]
        (default: %(default)s)""",
    )
    preprocess_args.add_argument(
        "--eddy-slm",
        "--eddy_slm",
        metavar="model",
        dest="participant.preprocess.eddy.slm",
        type=str,
        default=None,
        choices=["None", "linear", "quadratic"],
        help="""model for how diffusion gradients generate eddy currents
        (one of [%(choices)s]; default: %(default)s)""",
    )
    preprocess_args.add_argument(
        "--eddy-cnr-maps",
        "--eddy_cnr_maps",
        dest="participant.preprocess.eddy.cnr_maps",
        action="store_true",
        help="generate cnr maps",
    )
    preprocess_args.add_argument(
        "--eddy-repol",
        "--eddy_repol",
        dest="participant.preprocess.eddy.repol",
        action="store_true",
        help="replace outliers",
    )
    preprocess_args.add_argument(
        "--eddy-residuals",
        "--eddy_residuals",
        dest="participant.preprocess.eddy.residuals",
        action="store_true",
        help="generate 4d residual volume",
    )
    preprocess_args.add_argument(
        "--eddy-data-is-shelled",
        "--eddy_data_is_shelled",
        dest="participant.preprocess.eddy.shelled",
        action="store_true",
        help="skip eddy checking that data is shelled",
    )
    preprocess_args.add_argument(
        "--biascorrect-spacing",
        "--biascorrect_spacing",
        metavar="spacing",
        dest="participant.preprocess.biascorrect.spacing",
        type=float,
        default=100.0,
        help="initial mesh resolution in mm (default: %(default).2f)",
    )
    preprocess_args.add_argument(
        "--biascorrect-iters",
        "--biascorrect_iters",
        metavar="iterations",
        dest="participant.preprocess.biascorrect.iters",
        type=int,
        default=1000,
        help="number of iterations (default: %(default)d)",
    )
    preprocess_args.add_argument(
        "--biascorrect-shrink",
        "--biascorrect_shrink",
        metavar="factor",
        dest="participant.preprocess.biascorrect.shrink",
        type=int,
        default=4,
        help="shrink factor applied to spatial dimension (default: %(default)d)",
    )
    preprocess_args.add_argument(
        "--register-skip",
        "--register_skip",
        dest="participant.preprocess.register.skip",
        action="store_true",
        help="skip registration to participant structural t1w",
    )
    preprocess_args.add_argument(
        "--register-metric",
        "--register_metric",
        dest="participant.preprocess.register.metric",
        type=str,
        default="NMI",
        choices=["SSD", "MI", "NMI", "MAHAL"],
        help="""similarity metric to use for registration (
        one of [%(choices)s]; default: %(default)s)""",
    )
    preprocess_args.add_argument(
        "--register-iters",
        "--register_iters",
        metavar="iterations",
        dest="participant.preprocess.register.iters",
        type=str,
        default="50x50",
        help="number of iterations per level of multi-res (default: %(default)s",
    )


def _add_tractography_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with tractography analysis-level."""
    tractography_args = app_parser.add_argument_group(
        "tractography analysis-level options",
    )
    tractography_args.add_argument(
        "--single-shell",
        "--single_shell",
        dest="participant.tractography.single_shell",
        action="store_true",
        help="process single-shell data (default: %(default)s)",
    )
    tractography_args.add_argument(
        "--shells",
        metavar="shell",
        dest="participant.tractography.shells",
        nargs="*",
        type=int,
        help="space-separated list of b-values (b=0 must be included explicitly)",
    )
    tractography_args.add_argument(
        "--lmax",
        metavar="lmax",
        dest="participant.tractography.lmax",
        nargs="*",
        type=int,
        help="""maximum harmonic degree(s)
        (space-separated for multiple b-values, b=0 must be included explicitly)
        """,
    )
    tractography_args.add_argument(
        "--steps",
        metavar="steps",
        dest="participant.tractography.steps",
        type=float,
        help="step size (in mm) for tractography (default: 0.5 x voxel size)",
    )
    tractography_args.add_argument(
        "--tractography-method",
        "--tractography_method",
        metavar="method",
        dest="participant.tractography.method",
        type=str,
        default="wm",
        choices=["wm", "act"],
        help="tractography seeding method (one of [%(choices)s]; default: %(default)s)",
    )
    tractography_args.add_argument(
        "--cutoff",
        metavar="cutoff",
        dest="participant.tractography.cutoff",
        type=float,
        default=0.1,
        help="cutoff FOD amplitude for track termination (default: %(default).2f)",
    )
    tractography_args.add_argument(
        "--streamlines",
        metavar="streamlines",
        dest="participant.tractography.streamlines",
        type=int,
        default=10_000,
        help="number of streamlines to select (default %(default)d)",
    )


def _add_connectivity_args(app_parser: BidsAppArgumentParser) -> None:
    """Optional args associated with connectivity (connectivity) analysis-level."""
    connectivity_args = app_parser.add_argument_group(
        "connectivity analysis-level options",
    )
    connectivity_args.add_argument(
        "--atlas",
        metavar="atlas",
        dest="participant.connectivity.atlas",
        type=str,
        default=None,
        help="volumetric atlas name (assumed to be processed) for connectivity matrix",
    )
    connectivity_args.add_argument(
        "--radius",
        metavar="radius",
        dest="participant.connectivity.radius",
        type=float,
        default=2,
        help="distance (in mm) to map to nearest parcel (default: %(default).2f)",
    )
