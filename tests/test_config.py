import json
import logging
from pathlib import Path

import pytest
import yaml

from nhp_dwiproc.config import (
    ConnectivityConfig,
    GlobalOptsConfig,
    PreprocessConfig,
    utils,
)
from nhp_dwiproc.config.connectivity import ConnectomeConfig, TractMapConfig


class TestConfigIO:
    """Tests related to config IO (loading, etc)."""

    @pytest.mark.parametrize("extension", ["yaml", "yml"])
    def test_valid_ext(self, tmp_path: Path, extension: str):
        """Test running with valid extensions."""
        file_path = tmp_path / f"valid.{extension}"
        file_path.write_text(yaml.safe_dump({}))

        loaded = utils.load_config_file(file_path)
        assert loaded == {}

    def test_invalid_ext(self, tmp_path: Path):
        """Test running with invalid extension."""
        file_path = tmp_path / "invalid.ext"
        file_path.write_text(yaml.safe_dump({}))

        with pytest.raises(ValueError, match="Only YAML-based configuration files"):
            utils.load_config_file(file_path)

    def test_malformed_yaml(self, tmp_path: Path):
        """Test running with malformed configuraiton."""
        file_path = tmp_path / "malformed.yaml"
        file_path.write_text("key: [bad_list")

        with pytest.raises(yaml.YAMLError):
            utils.load_config_file(file_path)


class TestGenerateDescriptor:
    """Tests related to descriptor generation."""

    def test_valid_descriptor_generation(self, tmp_path: Path):
        """Test a valid descriptor is generated."""
        out_file = tmp_path / "dataset_description.json"

        app_name = "TestApp"
        version = "1.0.2"
        bids_version = "1.9.0"

        utils.generate_descriptor(
            app_name=app_name,
            version=version,
            bids_version=bids_version,
            out_fpath=out_file,
        )

        assert out_file.exists()
        with open(out_file, "r") as f:
            data = json.load(f)
        assert data["Name"] == app_name
        assert data["GeneratedBy"]["Version"] == version
        assert data["BIDSVersion"] == bids_version
        assert data["DatasetType"] == "derivative"
        assert data["GeneratedBy"]["Name"] == app_name

    def test_invalid_extension(self, tmp_path: Path, caplog: pytest.LogCaptureFixture):
        out_file = tmp_path / "descriptor.txt"

        with caplog.at_level(logging.WARNING):
            utils.generate_descriptor(
                app_name="TestApp", version="1.0.0", out_fpath=out_file
            )
        assert "not '.json'" in caplog.text
        assert out_file.exists()


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

    def test_valid_stage_config(self, tmp_path: Path, valid_cfg_yaml: Path):
        """Test running with a valid config."""
        global_opts = utils.build_config(
            cfg_class=GlobalOptsConfig, cfg_key="opts", cfg_file=valid_cfg_yaml
        )
        assert isinstance(global_opts, GlobalOptsConfig)
        assert global_opts.threads == 1
        assert global_opts.runner.name == "docker"
        preproc_opts = utils.build_config(
            cfg_class=PreprocessConfig, cfg_key="preprocess", cfg_file=valid_cfg_yaml
        )
        assert isinstance(preproc_opts, PreprocessConfig)
        assert preproc_opts.query.participant == "sub=='001'"

    def test_valid_stage_invalid_config(self, tmp_path: Path, invalid_cfg_yaml: Path):
        """Test running with ignored keys in invalid config."""
        global_opts = utils.build_config(
            cfg_class=GlobalOptsConfig, cfg_key="opts", cfg_file=invalid_cfg_yaml
        )
        assert not hasattr(global_opts, "invalid")
        preproc_opts = utils.build_config(
            cfg_class=PreprocessConfig, cfg_key="preprocess", cfg_file=invalid_cfg_yaml
        )
        assert not hasattr(preproc_opts, "invalid")

    def test_invalid_stage_config(self, tmp_path: Path, valid_cfg_yaml: Path):
        """Test to ensure stage specific params aren't passed to wrong stage."""
        conn_opts = utils.build_config(
            cfg_class=ConnectivityConfig,
            cfg_key="connectivity",
            cfg_file=valid_cfg_yaml,
        )
        assert conn_opts.query.participant is None

    def test_cli_overwrite(self, tmp_path: Path, valid_cfg_yaml: Path):
        """Test overwriting config parameters with CLI."""
        # Mock CLI arguments
        global_opts = utils.build_config(
            cfg_class=GlobalOptsConfig,
            cfg_key="opts",
            cfg_file=valid_cfg_yaml,
            ctx_params={"opts_runner": "singularity", "opts_threads": 4},
            cli_map={"opts_runner": "runner.name", "opts_threads": "threads"},
        )
        assert global_opts.runner.name == "singularity"
        assert global_opts.threads == 4


class TestBuildConfig:
    """Tests specific to building the configuration options."""

    def test_non_dataclass(self):
        """Test if dataclass is being used to build config."""
        NonDataClass = type("NonDataClass", (object,), {"invalid": "a"})
        with pytest.raises(TypeError):
            utils.build_config(cfg_class=NonDataClass, cfg_key="invalid")

    def test_dynamic_method_map(self):
        """Test dynamic method mapping."""
        method_map = {
            "method": {"connectome": ConnectomeConfig, "tract": TractMapConfig}
        }
        opts = utils.build_config(
            cfg_class=ConnectivityConfig,
            cfg_key="connectivity",
            dynamic_method_map=method_map,
        )
        assert opts.method == "connectome"


class TestMapParam:
    """Test parameter mapping."""

    def test_valid_prefix(self):
        """Test replacement of valid prefixes that exist."""
        new_vars_dict = utils.map_param("opt_", "", vars_dict={"opt_threads": 1})
        assert new_vars_dict.get("opt_threads") == "threads"

    def test_invalid_prefix(self):
        """Test non-replacement of prefix that does not exist."""
        new_vars_dict = utils.map_param("invalid_", "", vars_dict={"opt_threads": 1})
        assert "invalid" not in new_vars_dict
