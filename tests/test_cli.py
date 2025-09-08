from pathlib import Path

import pytest
from typer.testing import CliRunner

from nhp_dwiproc.cli import app

runner = CliRunner()


class TestCLI:
    """Tests for CLI commands and options."""

    @pytest.mark.parametrize("stage", ["preprocess", "reconstruction", "connectivity"])
    def test_valid_command(self, tmp_path: Path, stage: str):
        result = runner.invoke(app, args=[str(tmp_path), str(tmp_path), stage])
        assert result.exit_code == 0

    def test_invalid_command(self, tmp_path: Path):
        result = runner.invoke(app, args=[str(tmp_path), str(tmp_path), "invalid"])
        assert result.exit_code == 2

    @pytest.mark.parametrize("stage", ["preprocess", "reconstruction", "connectivity"])
    def test_valid_options(self, tmp_path: Path, stage: str):
        # Lots of valid parameters to choose from, only testing one valid
        result = runner.invoke(
            app, args=[str(tmp_path), str(tmp_path), stage, "--runner", "local"]
        )
        assert result.exit_code == 0

    def test_invalid_option(self, tmp_path: Path):
        result = runner.invoke(
            app, args=[str(tmp_path), str(tmp_path), "preprocess", "--invalid"]
        )
        assert result.exit_code == 2

    def test_valid_option_invalid_value(self, tmp_path: Path):
        result = runner.invoke(
            app,
            args=[str(tmp_path), str(tmp_path), "preprocess", "--runner", "invalid"],
        )
        assert result.exit_code == 2
