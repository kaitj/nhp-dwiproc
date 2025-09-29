import logging
from pathlib import Path

import pytest
from niwrap import DockerRunner, GraphRunner, LocalRunner, SingularityRunner

from nhp_dwiproc.app import utils
from nhp_dwiproc.config import GlobalOptsConfig, RunnerConfig


class TestAppInit:
    """Tests associated with testing app utilities."""

    def test_default_init(self, tmp_path: Path):
        """Test default initialization."""
        logger, runner = utils.initialize(
            output_dir=tmp_path,
            global_opts=GlobalOptsConfig(runner=RunnerConfig(name="local")),
        )
        assert isinstance(logger, logging.Logger)
        assert isinstance(runner, LocalRunner)

    @pytest.mark.parametrize("runner", ("docker", "podman"))
    def test_docker_init(self, tmp_path: Path, runner: str):
        """Test docker / podman initialization."""
        logger, runner = utils.initialize(
            output_dir=tmp_path,
            global_opts=GlobalOptsConfig(runner=RunnerConfig(name=runner)),
        )
        assert isinstance(logger, logging.Logger)
        assert isinstance(runner, DockerRunner)

    @pytest.mark.parametrize("runner", ("singularity", "apptainer"))
    def test_singularity_init(self, tmp_path: Path, runner: str):
        """Test singularity / apptainer initialization."""
        logger, runner = utils.initialize(
            output_dir=tmp_path,
            global_opts=GlobalOptsConfig(runner=RunnerConfig(name=runner, images={})),
        )
        assert isinstance(logger, logging.Logger)
        assert isinstance(runner, SingularityRunner)

    def test_graph_init(self, tmp_path: Path):
        """Test graph initialization."""
        logger, runner = utils.initialize(
            output_dir=tmp_path,
            global_opts=GlobalOptsConfig(graph=True),
        )
        assert isinstance(logger, logging.Logger)
        assert isinstance(runner, GraphRunner)

    def test_keep_work_dir(self, tmp_path: Path):
        """Test initialization with working directory saved."""
        logger, runner = utils.initialize(
            output_dir=tmp_path, global_opts=GlobalOptsConfig(work_keep=True)
        )
        assert isinstance(logger, logging.Logger)
        assert isinstance(runner, LocalRunner)
        # Test if parent directory exists, timestamp can be differ.
        assert (tmp_path / "working").exists()


class TestGenMrtrixConf:
    """Test generation of Mrtrix3 configuration."""

    def test_gen_conf_local(self, tmp_path: Path):
        runner = LocalRunner(data_dir=tmp_path)
        global_opts = GlobalOptsConfig()
        utils.generate_mrtrix_conf(global_opts=global_opts, runner=runner)
        cfg_fpath = runner.data_dir / f"{runner.uid}_cfgs" / ".mrtrix.conf"
        assert cfg_fpath.exists()
        assert f"BZeroThreshold: {global_opts.b0_thresh}" in cfg_fpath.read_text()

    def test_gen_conf_docker_valid(self, tmp_path: Path):
        runner = DockerRunner(data_dir=tmp_path)
        utils.generate_mrtrix_conf(
            global_opts=GlobalOptsConfig(runner=RunnerConfig(name="docker")),
            runner=runner,
        )
        cfg_fpath = runner.data_dir / f"{runner.uid}_cfgs" / ".mrtrix.conf"
        assert cfg_fpath.exists()
        assert runner.docker_extra_args == [
            "--mount",
            f"type=bind,source={cfg_fpath},target={cfg_fpath},readonly",
        ]

    def test_gen_conf_docker_invalid(self, tmp_path: Path):
        with pytest.raises(TypeError, match="Expected DockerRunner"):
            utils.generate_mrtrix_conf(
                global_opts=GlobalOptsConfig(runner=RunnerConfig(name="docker")),
                runner=LocalRunner(data_dir=tmp_path),
            )

    def test_gen_conf_singularity_valid(self, tmp_path: Path):
        runner = SingularityRunner(data_dir=tmp_path)
        utils.generate_mrtrix_conf(
            global_opts=GlobalOptsConfig(runner=RunnerConfig(name="singularity")),
            runner=runner,
        )
        cfg_fpath = runner.data_dir / f"{runner.uid}_cfgs" / ".mrtrix.conf"
        assert cfg_fpath.exists()
        assert runner.singularity_extra_args == [
            "--bind",
            f"{cfg_fpath}:{cfg_fpath}:ro",
        ]

    def test_gen_conf_singularity_invalid(self, tmp_path: Path):
        with pytest.raises(TypeError, match="Expected SingularityRunner"):
            utils.generate_mrtrix_conf(
                global_opts=GlobalOptsConfig(runner=RunnerConfig(name="singularity")),
                runner=LocalRunner(data_dir=tmp_path),
            )
