import logging
import tempfile
from pathlib import Path

import pytest
from niwrap import DockerRunner, GraphRunner, LocalRunner, SingularityRunner

from nhp_dwiproc.app import utils
from nhp_dwiproc.config import (
    ConnectivityConfig,
    GlobalOptsConfig,
    PreprocessConfig,
    QueryConfig,
    RunnerConfig,
    preprocess,
)


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


class TestValidateGlobalOpts:
    """Test validation of global options."""

    @pytest.mark.parametrize("stage", ("index", "reconstruction", "connectivity"))
    def test_ignored_stages(self, stage: str):
        """Nothing should happen - fail on exception."""
        utils.validate_opts(stage=stage)

    def test_participant_query_valid(self):
        utils.validate_opts(
            stage="index", query_opts=QueryConfig(participant="sub=='abc' & ses=='123'")
        )

    def test_participant_query_invalid(self):
        with pytest.raises(ValueError, match="Only 'sub' and 'ses' are valid"):
            utils.validate_opts(
                stage="index", query_opts=QueryConfig(participant="sub=='xx' & run=1")
            )


class TestValidatePreprocessOpts:
    """Test validation of preprocess options."""

    def test_preproc_invalid_instance(self):
        with pytest.raises(TypeError, match="Expected PreprocessConfig"):
            utils.validate_opts(stage="preprocess", stage_opts=ConnectivityConfig())

    @pytest.mark.parametrize("pe_dirs", (["j"], ["j-"], ["i", "i-"], ["k"]))
    def test_phase_encode_valid(self, pe_dirs: list[str]):
        utils.validate_opts(
            stage="preprocess",
            stage_opts=PreprocessConfig(
                metadata=preprocess.MetadataConfig(pe_dirs=pe_dirs)
            ),
        )

    def test_phase_encode_invalid_multiple(self):
        with pytest.raises(ValueError, match="More than 2"):
            utils.validate_opts(
                stage="preprocess",
                stage_opts=PreprocessConfig(
                    metadata=preprocess.MetadataConfig(pe_dirs=["j", "j", "j-"])
                ),
            )

    def test_phase_encode_invalid_value(self):
        with pytest.raises(ValueError, match="Invalid phase-encode"):
            utils.validate_opts(
                stage="preprocess",
                stage_opts=PreprocessConfig(
                    metadata=preprocess.MetadataConfig(pe_dirs=["x"])
                ),
            )

    @pytest.mark.parametrize("cfg", ("b02b0", "b02b0_macaque", "b02b0_marmoset"))
    def test_topup_valid_included_cfgs(self, cfg: str):
        utils.validate_opts(
            stage="preprocess",
            stage_opts=PreprocessConfig(
                undistort=preprocess.UndistortionConfig(
                    opts=preprocess.UndistortionOpts(
                        topup=preprocess.TopupConfig(config=cfg)
                    )
                )
            ),
        )

    def test_topup_valid_custom_cfgs(self, tmp_path: Path):
        with tempfile.NamedTemporaryFile(dir=tmp_path, suffix=".cnf") as cfg:
            utils.validate_opts(
                stage="preprocess",
                stage_opts=PreprocessConfig(
                    undistort=preprocess.UndistortionConfig(
                        opts=preprocess.UndistortionOpts(
                            topup=preprocess.TopupConfig(config=cfg.name)
                        )
                    )
                ),
            )

    def test_topup_missing_custom_cfg(self):
        with pytest.raises(FileNotFoundError, match="not found"):
            utils.validate_opts(
                stage="preprocess",
                stage_opts=PreprocessConfig(
                    undistort=preprocess.UndistortionConfig(
                        opts=preprocess.UndistortionOpts(
                            topup=preprocess.TopupConfig(config="missing.cnf")
                        )
                    )
                ),
            )

    def test_topup_invalid_instance(self):
        with pytest.raises(TypeError, match="Expected TopupConfig"):
            utils.validate_opts(
                stage="preprocess",
                stage_opts=PreprocessConfig(
                    undistort=preprocess.UndistortionConfig(
                        opts=preprocess.UndistortionOpts(topup=ConnectivityConfig())
                    )
                ),
            )
