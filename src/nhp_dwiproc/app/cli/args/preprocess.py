"""Sub-module containing preprocessing optional arguments."""

from argparse import _ArgumentGroup

from bidsapp_helper.parser import BidsAppArgumentParser


def add_preprocess_args(app_parser: BidsAppArgumentParser) -> None:
    """Preprocessing analysis-level arguments."""
    add_funcs = (
        _add_metadata,
        _add_denoise,
        _add_unring,
        _add_eddymotion,
        _add_topup,
        _add_eddy,
        _add_biascorrect,
        _add_register,
    )

    arg_group = app_parser.add_argument_group("preprocessing analysis-level options")
    arg_group.add_argument(
        "--undistort-method",
        "--undistort_method",
        metavar="method",
        dest="participant.preprocess.undistort.method",
        type=str,
        default="topup",
        choices=["topup", "fieldmap", "fugue", "eddymotion"],
        help="distortion correct method (one of [%(choices)s]; default: %(default)s)",
    )
    for add_func in add_funcs:
        add_func(arg_group)


def _add_metadata(arg_group: _ArgumentGroup) -> None:
    """Metadata associated arguments."""
    arg_group.add_argument(
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
    arg_group.add_argument(
        "--echo-spacing",
        "--echo_spacing",
        metavar="spacing",
        dest="participant.preprocess.metadata.echo_spacing",
        type=float,
        default=0.0001,
        help="""estimated echo spacing to use for all dwi acquisitions, value in
        metadata (JSON) file will take priority (default: %(default).4f)""",
    )


def _add_denoise(arg_group: _ArgumentGroup) -> None:
    """Denoising associated arguments."""
    arg_group.add_argument(
        "--denoise-skip",
        "--denoise_skip",
        dest="participant.preprocess.denoise.skip",
        action="store_true",
        help="skip denoising step",
    )
    arg_group.add_argument(
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
    arg_group.add_argument(
        "--denoise-map",
        "--denoise_map",
        dest="participant.preprocess.denoise.map",
        action="store_true",
        help="output noise map (estimated level 'sigma' in the data)",
    )
    arg_group.add_argument(
        "--denoise-estimator",
        "--denoise_estimator",
        metavar="estimator",
        dest="participant.preprocess.denoise.estimator",
        type=str,
        default="Exp2",
        choices=["Exp1", "Exp2"],
        help="noise level estimator (one of [%(choices)s]; default: %(default)s)",
    )


def _add_unring(arg_group: _ArgumentGroup) -> None:
    """Unringing associated arguments."""
    arg_group.add_argument(
        "--unring-skip",
        "--unring_skip",
        dest="participant.preprocess.unring.skip",
        action="store_true",
        help="skip unringing step",
    )
    arg_group.add_argument(
        "--unring-axes",
        "--unring_axes",
        metavar="axes",
        dest="participant.preprocess.unring.axes",
        nargs="*",
        type=int,
        default=None,
        help="slice axes (space seperated; default: 0,1 - e.g. x-y)",
    )
    arg_group.add_argument(
        "--unring-nshifts",
        "--unring_nshifts",
        metavar="nshifts",
        dest="participant.preprocess.unring.nshifts",
        type=int,
        default=20,
        help="discretization of subpixel spacing (default: %(default)d)",
    )
    arg_group.add_argument(
        "--unring-minw",
        "--unring_minw",
        metavar="minw",
        dest="participant.preprocess.unring.minW",
        type=int,
        default=1,
        help="left border of window used for computation",
    )
    arg_group.add_argument(
        "--unring-maxw",
        "--unring_maxw",
        metavar="maxw",
        dest="participant.preprocess.unring.maxW",
        type=int,
        default=3,
        help="right border of window used for computation",
    )


def _add_eddymotion(arg_group: _ArgumentGroup) -> None:
    """Eddymotion associated arguments."""
    arg_group.add_argument(
        "--eddymotion-iters",
        "--eddymotion_iters",
        metavar="iterations",
        dest="participant.preprocess.eddymotion.iters",
        type=int,
        default=2,
        help="number of iterations to repeat for eddymotion",
    )


def _add_topup(arg_group: _ArgumentGroup) -> None:
    """FSL Topup associated arguments."""
    arg_group.add_argument(
        "--topup-skip",
        "--topup_skip",
        dest="participant.preprocess.topup.skip",
        action="store_true",
        help="skip FSL topup step",
    )
    arg_group.add_argument(
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


def _add_eddy(arg_group: _ArgumentGroup) -> None:
    """FSL Eddy associated arguments."""
    arg_group.add_argument(
        "--eddy-skip",
        "--eddy_skip",
        dest="participant.preprocess.eddy.skip",
        action="store_true",
        help="skip eddy correction step",
    )
    arg_group.add_argument(
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
    arg_group.add_argument(
        "--eddy-cnr-maps",
        "--eddy_cnr_maps",
        dest="participant.preprocess.eddy.cnr_maps",
        action="store_true",
        help="generate cnr maps",
    )
    arg_group.add_argument(
        "--eddy-repol",
        "--eddy_repol",
        dest="participant.preprocess.eddy.repol",
        action="store_true",
        help="replace outliers",
    )
    arg_group.add_argument(
        "--eddy-residuals",
        "--eddy_residuals",
        dest="participant.preprocess.eddy.residuals",
        action="store_true",
        help="generate 4d residual volume",
    )
    arg_group.add_argument(
        "--eddy-data-is-shelled",
        "--eddy_data_is_shelled",
        dest="participant.preprocess.eddy.shelled",
        action="store_true",
        help="skip eddy checking that data is shelled",
    )


def _add_biascorrect(arg_group: _ArgumentGroup) -> None:
    """Biascorrection associated arguments."""
    arg_group.add_argument(
        "--biascorrect-spacing",
        "--biascorrect_spacing",
        metavar="spacing",
        dest="participant.preprocess.biascorrect.spacing",
        type=float,
        default=100.0,
        help="initial mesh resolution in mm (default: %(default).2f)",
    )
    arg_group.add_argument(
        "--biascorrect-iters",
        "--biascorrect_iters",
        metavar="iterations",
        dest="participant.preprocess.biascorrect.iters",
        type=int,
        default=1000,
        help="number of iterations (default: %(default)d)",
    )
    arg_group.add_argument(
        "--biascorrect-shrink",
        "--biascorrect_shrink",
        metavar="factor",
        dest="participant.preprocess.biascorrect.shrink",
        type=int,
        default=4,
        help="shrink factor applied to spatial dimension (default: %(default)d)",
    )


def _add_register(arg_group: _ArgumentGroup) -> None:
    """Registration associated arguments."""
    arg_group.add_argument(
        "--register-skip",
        "--register_skip",
        dest="participant.preprocess.register.skip",
        action="store_true",
        help="skip registration to participant structural t1w",
    )
    arg_group.add_argument(
        "--register-metric",
        "--register_metric",
        dest="participant.preprocess.register.metric",
        type=str,
        default="NMI",
        choices=["SSD", "MI", "NMI", "MAHAL"],
        help="""similarity metric to use for registration (
        one of [%(choices)s]; default: %(default)s)""",
    )
    arg_group.add_argument(
        "--register-iters",
        "--register_iters",
        metavar="iterations",
        dest="participant.preprocess.register.iters",
        type=str,
        default="50x50",
        help="number of iterations per level of multi-res (default: %(default)s",
    )
