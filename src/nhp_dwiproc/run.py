#!/usr/bin/env python
"""Main entrypoint of code."""

from . import app


def main() -> None:
    """Application."""
    logger = app.utils.setup_logger()

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
