"""Sub-module containing general optional arguments."""

import pathlib as pl

from bidsapp_helper.parser import BidsAppArgumentParser


def add_optional_args(app_parser: BidsAppArgumentParser) -> None:
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
        help="bids2table index path (default: {bids_dir}/index.parquet)",
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
