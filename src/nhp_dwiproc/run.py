#!/usr/bin/env python
"""Main entrypoint of code."""

import shutil

from . import app


def main() -> None:
    """Application."""
    # Initialize app and parse arguments
    cfg = app.parser().parse_args()

    # Run workflow
    logger, runner = app.initialize(cfg=cfg)
    match analysis_level := cfg["analysis_level"]:
        case "index":
            app.analysis_levels.index.run(cfg=cfg, logger=logger)
        case "tractography":
            app.analysis_levels.tractography.run(cfg=cfg, logger=logger)
        case "connectivity":
            app.analysis_levels.connectivity.run(cfg=cfg, logger=logger)

    if analysis_level in ["tractography", "connectivity"]:
        app.generate_descriptor(cfg=cfg, out_fname="dataset_description.json")

    # Finish cleaning up workflow
    shutil.rmtree(cfg["opt.working_dir"])

    # Print graph
    if cfg["opt.graph"]:
        logger.info("Printing mermaid workflow graph")
        print(runner.mermaid())  # type: ignore


if __name__ == "__main__":
    main()
