#!/usr/bin/env python
"""Main entrypoint of code."""

from . import app


def main() -> None:
    """Application."""
    # Initialize app and parse arguments
    cfg = app.parser().parse_args()

    # Run workflow
    logger = app.initialize(cfg=cfg)
    match cfg["analysis_level"]:
        case "index":
            app.analysis_levels.index.run(cfg=cfg, logger=logger)
        case "participant":
            app.analysis_levels.participant.run(cfg=cfg, logger=logger)
            app.generate_descriptor(cfg=cfg, out_fname="dataset_description.json")

    # Finish cleaning up workflow
    app.utils.clean_up(cfg=cfg, logger=logger)


if __name__ == "__main__":
    main()
