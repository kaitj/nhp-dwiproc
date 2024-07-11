#!/usr/bin/env python
"""Main entrypoint of code."""

import logging
import sys

from . import app

# Setup logger
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s %(name)s %(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console = logging.StreamHandler(sys.stdout)
console.setLevel(100)
logger = logging.getLogger(__name__)
logger.addHandler(console)


def main() -> None:
    """Application."""
    # Parse arguments
    args = app.parser().parse_args()

    match args.analysis_level:
        case "index":
            app.analysis_levels.index.run(args=args, logger=logger)
        case "participant":
            app.analysis_levels.participant.run(args=args, logger=logger)

    app.descriptor(args.output_dir / "pipeline_description.json")


if __name__ == "__main__":
    main()
