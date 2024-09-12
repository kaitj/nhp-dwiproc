#!/usr/bin/env python
"""Main entrypoint of code."""

import shutil

from nhp_dwiproc import app


def main() -> None:
    """Application."""
    # Initialize app and parse arguments
    cfg = app.parser().parse_args()

    # Validate config
    app.validate_cfg(cfg=cfg)

    # Run workflow
    logger, runner = app.initialize(cfg=cfg)
    match analysis_level := cfg["analysis_level"]:
        case "index":
            app.analysis_levels.index.run(cfg=cfg, logger=logger)
        case "preprocess":
            app.analysis_levels.preprocess.run(cfg=cfg, logger=logger)
        case "tractography":
            app.analysis_levels.tractography.run(cfg=cfg, logger=logger)
        case "connectivity":
            app.analysis_levels.connectivity.run(cfg=cfg, logger=logger)

    if analysis_level != "index":
        app.generate_descriptor(cfg=cfg, out_fname="dataset_description.json")

    # Finish cleaning up workflow
    if not cfg["opt.keep_tmp"]:
        shutil.rmtree(runner.base.data_dir)

    # Print graph
    if cfg["opt.graph"]:
        logger.info("Printing mermaid workflow graph")
        logger.info(runner.node_graph_mermaid())  # type: ignore


if __name__ == "__main__":
    main()
