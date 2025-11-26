import json
import logging
from pathlib import Path
from types import SimpleNamespace

import pytest
import typer
from typer.testing import CliRunner

from nhp_dwiproc.cli import app, utils
from nhp_dwiproc.config.shared import GlobalOptsConfig

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


class TestSetupLogging:
    """Test logging level setup."""

    def test_verbose_zero(self):
        """Test with no verbosity."""
        level = utils.setup_logging(0)
        assert level == logging.CRITICAL + 1

    def test_verbose_one(self):
        """Test with verbosity level 1."""
        level = utils.setup_logging(1)
        assert level == logging.INFO

    def test_verbose_two(self):
        """Test with verbosity level 2."""
        level = utils.setup_logging(2)
        assert level == logging.DEBUG

    def test_verbose_exceeds_max(self):
        """Test with verbosity exceeding available levels."""
        level = utils.setup_logging(10)
        assert level == logging.DEBUG

    def test_verbose_negative(self):
        """Test with negative verbosity."""
        level = utils.setup_logging(-1)
        assert level == logging.CRITICAL + 1


class TestBuildGlobalOpts:
    """Test building global options configuration."""

    def test_build_opts_minimal(self):
        """Test building with minimal parameters."""
        ctx_params = {
            "opts_work_dir": Path("/tmp/work"),
            "opts_b0_thresh": 10,
        }
        result = utils.build_global_opts(ctx_params, cfg_file=None)
        assert isinstance(result, GlobalOptsConfig)
        assert result.work_dir == Path("/tmp/work")
        assert result.b0_thresh == 10

    def test_build_opts_with_runner(self):
        """Test building with runner configuration."""
        ctx_params = {
            "opts_work_dir": Path("/tmp/work"),
            "opts_runner": "docker",
            "opts_images": {"some": "image"},
        }
        result = utils.build_global_opts(ctx_params, cfg_file=None)
        assert isinstance(result, GlobalOptsConfig)
        assert result.runner.name == "docker"

    def test_build_opts_custom_prefix(self):
        """Test building with custom prefix."""
        ctx_params = {
            "custom_work_dir": Path("/tmp/work"),
            "custom_b0_thresh": 15,
        }
        result = utils.build_global_opts(ctx_params, cfg_file=None, prefix="custom_")
        assert isinstance(result, GlobalOptsConfig)
        assert result.work_dir == Path("/tmp/work")
        assert result.b0_thresh == 15

    def test_build_opts_filters_non_prefix(self):
        """Test that non-prefixed parameters are ignored."""
        ctx_params = {
            "opts_work_dir": Path("/tmp/work"),
            "other_param": "should_be_ignored",
            "opts_b0_thresh": 20,
        }
        result = utils.build_global_opts(ctx_params, cfg_file=None)
        assert isinstance(result, GlobalOptsConfig)
        # Should not raise error from 'other_param'

    def test_build_opts_with_config_file(self, tmp_path: Path):
        """Test building with configuration file."""
        cfg_content = """
opts:
  work_dir: /tmp/from_config
  b0_thresh: 25
"""
        cfg_file = tmp_path / "config.yaml"
        cfg_file.write_text(cfg_content)

        ctx_params = {"opts_work_dir": Path("/tmp/from_cli")}
        result = utils.build_global_opts(ctx_params, cfg_file=cfg_file)
        assert isinstance(result, GlobalOptsConfig)
        # CLI should override config file
        assert result.work_dir == Path("/tmp/from_cli")

    def test_build_opts_empty_params(self):
        """Test building with empty parameters."""
        result = utils.build_global_opts({}, cfg_file=None)
        assert isinstance(result, GlobalOptsConfig)


class TestFinalizeStage:
    """Test stage finalization."""

    def test_finalize_basic(self, tmp_path: Path):
        """Test basic finalization."""
        logger = logging.getLogger("test")
        ctx = SimpleNamespace(
            log_level=logging.INFO, app="test_app", version="1.0.0", output_dir=tmp_path
        )
        utils.finalize_stage(ctx, logger, include_descriptor=True)
        assert logger.level == logging.INFO
        descriptor_path = tmp_path / "dataset_description.json"
        assert descriptor_path.exists()
        with open(descriptor_path) as f:
            descriptor = json.load(f)
        assert descriptor["Name"] == "test_app"
        assert descriptor["GeneratedBy"]["Version"] == "1.0.0"

    def test_finalize_without_descriptor(self, tmp_path: Path):
        """Test finalization without descriptor generation."""
        logger = logging.getLogger("test_no_desc")
        ctx = SimpleNamespace(
            log_level=logging.DEBUG,
            app="test_app",
            version="1.0.0",
            output_dir=tmp_path,
        )
        utils.finalize_stage(ctx, logger, include_descriptor=False)
        assert logger.level == logging.DEBUG
        descriptor_path = tmp_path / "dataset_description.json"
        assert not descriptor_path.exists()

    def test_finalize_log_level_change(self, tmp_path: Path):
        """Test that log level is updated correctly."""
        logger = logging.getLogger("test_level")
        initial_level = logging.WARNING
        logger.setLevel(initial_level)
        ctx = SimpleNamespace(
            log_level=logging.ERROR,
            app="test_app",
            version="1.0.0",
            output_dir=tmp_path,
        )
        assert logger.level == initial_level
        utils.finalize_stage(ctx, logger, include_descriptor=False)
        assert logger.level == logging.ERROR

    def test_finalize_complex_namespace(self, tmp_path: Path):
        """Test finalization with complex nested namespace."""
        logger = logging.getLogger("test_complex")
        ctx = SimpleNamespace(
            log_level=logging.INFO,
            app="test_app",
            version="2.0.0",
            output_dir=tmp_path,
            nested=SimpleNamespace(
                param1="value1",
                param2=42,
            ),
            list_param=[1, 2, 3],
        )
        utils.finalize_stage(ctx, logger, include_descriptor=True)
        assert logger.level == logging.INFO

    def test_finalize_descriptor_overwrites(self, tmp_path: Path):
        """Test that descriptor file is overwritten if it exists."""
        logger = logging.getLogger("test_overwrite")
        descriptor_path = tmp_path / "dataset_description.json"
        descriptor_path.write_text('{"Name": "old_app"}')
        ctx = SimpleNamespace(
            log_level=logging.INFO, app="new_app", version="3.0.0", output_dir=tmp_path
        )
        utils.finalize_stage(ctx, logger, include_descriptor=True)
        with open(descriptor_path) as f:
            descriptor = json.load(f)
        assert descriptor["Name"] == "new_app"

    @pytest.mark.parametrize(
        "log_level",
        [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL],
    )
    def test_finalize_various_log_levels(self, tmp_path: Path, log_level: int):
        """Test finalization with various log levels."""
        logger = logging.getLogger(f"test_{log_level}")
        ctx = SimpleNamespace(
            log_level=log_level,
            app="test_app",
            version="1.0.0",
            output_dir=tmp_path,
        )

        utils.finalize_stage(ctx, logger, include_descriptor=False)
        assert logger.level == log_level


class TestJsonDictCallback:
    """Test JSON dict callback for CLI parsing."""

    def test_valid_json_dict(self):
        """Test parsing valid JSON dictionary."""
        json_str = '{"key1": "value1", "key2": "value2"}'
        result = utils.json_dict_callback(json_str)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_valid_empty_dict(self):
        """Test parsing empty JSON dictionary."""
        result = utils.json_dict_callback("{}")
        assert result == {}

    def test_none_value(self):
        """Test with None value - should return None."""
        result = utils.json_dict_callback(None)
        assert result is None

    def test_valid_nested_dict(self):
        """Test parsing nested JSON dictionary."""
        json_str = '{"outer": {"inner": "value"}}'
        result = utils.json_dict_callback(json_str)
        assert result == {"outer": {"inner": "value"}}

    def test_invalid_json(self):
        """Test with invalid JSON - should raise BadParameter."""
        with pytest.raises(typer.BadParameter, match="Invalid JSON"):
            utils.json_dict_callback('{"invalid": }')

    def test_invalid_json_missing_quote(self):
        """Test with malformed JSON missing quote."""
        with pytest.raises(typer.BadParameter, match="Invalid JSON"):
            utils.json_dict_callback('{"key": "value}')

    def test_invalid_json_trailing_comma(self):
        """Test with invalid trailing comma."""
        with pytest.raises(typer.BadParameter, match="Invalid JSON"):
            utils.json_dict_callback('{"key": "value",}')

    def test_json_with_special_chars(self):
        """Test parsing JSON with special characters."""
        json_str = '{"path": "/usr/local/bin", "flag": "--verbose"}'
        result = utils.json_dict_callback(json_str)
        assert result == {"path": "/usr/local/bin", "flag": "--verbose"}

    def test_json_with_numbers(self):
        """Test parsing JSON with numeric values."""
        json_str = '{"count": 42, "rate": 3.14}'
        result = utils.json_dict_callback(json_str)
        assert result == {"count": 42, "rate": 3.14}

    def test_json_with_boolean(self):
        """Test parsing JSON with boolean values."""
        json_str = '{"enabled": true, "debug": false}'
        result = utils.json_dict_callback(json_str)
        assert result == {"enabled": True, "debug": False}

    def test_json_with_null(self):
        """Test parsing JSON with null value."""
        json_str = '{"value": null}'
        result = utils.json_dict_callback(json_str)
        assert result == {"value": None}

    def test_empty_string(self):
        """Test with empty string - should raise BadParameter."""
        with pytest.raises(typer.BadParameter, match="Invalid JSON"):
            utils.json_dict_callback("")

    def test_non_dict_json_list(self):
        """Test parsing JSON list (still valid JSON)."""
        json_str = '["item1", "item2"]'
        result = utils.json_dict_callback(json_str)
        assert result == ["item1", "item2"]

    def test_non_dict_json_string(self):
        """Test parsing JSON string (still valid JSON)."""
        json_str = '"just a string"'
        result = utils.json_dict_callback(json_str)
        assert result == "just a string"
