from pathlib import Path

import pytest
import yaml
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


class TestAppOptions:
    """Tests for passing options via config and CLI."""

    @pytest.fixture
    def valid_cfg_yaml(self, tmp_path: Path):
        valid_cfg = {
            "opts": {"threads": 1, "runner": {"name": "docker"}},
            "preprocess": {"query": {"participant": "sub=='001'"}},
        }
        file_path = tmp_path / "valid.yaml"
        file_path.write_text(yaml.safe_dump(valid_cfg))

        return file_path

    @pytest.fixture
    def invalid_cfg_yaml(self, tmp_path: Path):
        valid_cfg = {
            "opts": {"threads": 1, "runner": {"name": "docker"}},
            "preprocess": {"query": {"participant": "sub=='001'"}},
            "invalid": "value",
        }
        file_path = tmp_path / "valid.yaml"
        file_path.write_text(yaml.safe_dump(valid_cfg))

        return file_path

    def test_valid_config_stage(self, tmp_path: Path, valid_cfg_yaml: Path):
        """Test running with a valid config."""
        result = runner.invoke(
            app,
            args=[
                str(tmp_path),
                str(tmp_path),
                "preprocess",
                "--config",
                str(valid_cfg_yaml),
            ],
        )
        for expected in [str(valid_cfg_yaml), "docker", "sub=='001"]:
            assert expected in result.output

    def test_valid_stage_invalid_config(self, tmp_path: Path, invalid_cfg_yaml: Path):
        """Test running with ignored keys in invalid config."""
        result = runner.invoke(
            app,
            args=[
                str(tmp_path),
                str(tmp_path),
                "preprocess",
                "--config",
                str(invalid_cfg_yaml),
            ],
        )
        assert result.exit_code == 0
        for expected in [str(invalid_cfg_yaml), "docker", "sub=='001"]:
            assert expected in result.output
        assert "value" not in result.output

    def test_invalid_stage_config(self, tmp_path: Path, valid_cfg_yaml: Path):
        """Test to ensure stage specific params aren't passed to wrong stage."""
        result = runner.invoke(
            app,
            args=[
                str(tmp_path),
                str(tmp_path),
                "connectivity",
                "--config",
                str(valid_cfg_yaml),
            ],
        )
        for expected in [str(valid_cfg_yaml), "docker"]:
            assert expected in result.output
        assert "sub=='001'" not in result.output

    def test_cli_overwrite(self, tmp_path: Path, valid_cfg_yaml: Path):
        """Test overwriting config parameters with CLI."""
        result = runner.invoke(
            app,
            args=[
                str(tmp_path),
                str(tmp_path),
                "preprocess",
                "--config",
                str(valid_cfg_yaml),
                "--runner",
                "singularity",
                "--threads",
                "4",
            ],
        )
        for expected in [
            str(valid_cfg_yaml),
            "sub=='001",
            "singularity",
            "threads=4",
        ]:
            assert expected in result.output
