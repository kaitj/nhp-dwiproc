import json
import logging
from pathlib import Path

import pytest
import yaml

from nhp_dwiproc.config import utils


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
