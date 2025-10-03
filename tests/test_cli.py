from pathlib import Path

import pytest
from typer.testing import CliRunner

from nhp_dwiproc.cli import app

runner = CliRunner()


class TestCLI:
    """Tests for CLI commands and options."""

    @pytest.mark.parametrize("stage", ["preprocess", "reconstruction", "connectivity"])
    def test_valid_command(self, tmp_path: Path, stage: str):
        str_path = str(tmp_path)
        result = runner.invoke(app, args=[str_path, str_path, stage, "--help"])
        assert result.exit_code == 0

    def test_invalid_command(self, tmp_path: Path):
        str_path = str(tmp_path)
        result = runner.invoke(app, args=[str_path, str_path, "invalid", "--help"])
        assert result.exit_code == 2

    @pytest.mark.parametrize("stage", ["preprocess", "reconstruction", "connectivity"])
    def test_valid_options(self, tmp_path: Path, stage: str):
        # Lots of valid parameters to choose from, only testing one valid
        str_path = str(tmp_path)
        result = runner.invoke(
            app,
            args=[
                str_path,
                str_path,
                stage,
                "--runner",
                "local",
                "--work-dir",
                str_path,
                "--help",
            ],
        )
        assert result.exit_code == 0

    def test_invalid_option(self, tmp_path: Path):
        str_path = str(tmp_path)
        result = runner.invoke(
            app,
            args=[
                str_path,
                str_path,
                "preprocess",
                "--work-dir",
                str_path,
                "--invalid",
            ],
        )
        assert result.exit_code == 2

    def test_valid_option_invalid_value(self, tmp_path: Path):
        str_path = str(tmp_path)
        result = runner.invoke(
            app,
            args=[
                str_path,
                str_path,
                "preprocess",
                "--work-dir",
                str_path,
                "--runner",
                "invalid",
            ],
        )
        assert result.exit_code == 2

    def test_version(self):
        result = runner.invoke(app, args=["--version"])
        assert result.exit_code == 0
        assert "NHP-DWIProc version: " in result.output
