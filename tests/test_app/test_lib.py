import logging

import numpy as np
import pytest

from nhp_dwiproc.app.lib import eddymotion, metadata


class TestPEDir:
    """Tests for phase-encode direction in metadata."""

    def test_missing_pe_info(self):
        with pytest.raises(ValueError, match="'PhaseEncodingDirection' not found"):
            metadata.phase_encode_dir(idx=0, dwi_json={}, pe_dirs=None)

    def test_set_pe_dirs(self):
        pe_dir = metadata.phase_encode_dir(idx=0, dwi_json={}, pe_dirs=["j"])
        assert pe_dir == "j"

    def test_assume_pe_dir(self, caplog: pytest.LogCaptureFixture):
        logger = logging.getLogger(__name__)
        pe_dir = metadata.phase_encode_dir(
            idx=0, dwi_json={"PhaseEncodingAxis": "j"}, pe_dirs=None, logger=logger
        )
        assert "Assuming 'PhaseEncodingDirection'" in caplog.text
        assert pe_dir == "j"


class TestEchoSpacing:
    """Tests for setting echo spacing."""

    def test_missing_echo_spacing(self):
        with pytest.raises(ValueError, match="Unable to assume 'EffectiveEchoSpacing'"):
            metadata.echo_spacing(dwi_json={}, echo_spacing=None)

    def test_provided_echo_spacing(self, caplog: pytest.LogCaptureFixture):
        caplog.set_level(logging.INFO)
        echo = metadata.echo_spacing(
            dwi_json={}, echo_spacing="0.001", logger=logging.getLogger(__name__)
        )
        assert "provided echo spacing" in caplog.text
        assert echo == 0.001

    def test_estimated_echo_spacing(self, caplog: pytest.LogCaptureFixture):
        echo = metadata.echo_spacing(
            dwi_json={
                "EstimatedEffectiveEchoSpacing": 0.001,
            },
            echo_spacing=None,
            logger=logging.getLogger(__name__),
        )
        assert "Assuming 'EffectiveEchoSpacing'" in caplog.text
        assert echo == 0.001


class TestSphericalFootprint:
    """Tests for _spherical_footprint helper."""

    def test_shape(self):
        fp = eddymotion._spherical_footprint(radius=3)
        assert fp.shape == (7, 7, 7)

    def test_symmetry(self):
        fp = eddymotion._spherical_footprint(radius=2)
        # Check center is True
        center = fp.shape[0] // 2
        assert fp[center, center, center]
        # Check symmetry along each axis
        assert np.array_equal(fp, np.flip(fp, axis=0))
        assert np.array_equal(fp, np.flip(fp, axis=1))
        assert np.array_equal(fp, np.flip(fp, axis=2))

    def test_count_radius_1(self):
        fp = eddymotion._spherical_footprint(radius=1)
        # 3x3x3 sphere: center + 6 adjacent = 7 voxels within distance <= 1
        assert fp.sum() == 7

    def test_count_radius_2(self):
        fp = eddymotion._spherical_footprint(radius=2)
        # 5x5x5 sphere: all within sqrt(3) ~ 1.732 of center
        # Corners: distance sqrt(3*2^2) = sqrt(12) ~ 3.46 > 2, excluded
        assert fp.sum() > 0
        assert fp.sum() < 125  # Not all 125 voxels


class TestTrivialB0Model:
    """Tests for TrivialB0Model."""

    def test_fit_noop(self):
        s0 = np.ones((10, 10, 10), dtype="float32")
        model = eddymotion.TrivialB0Model(S0=s0)
        data = np.random.rand(10, 10, 10, 5).astype("float32")
        model.fit(data)  # Should not raise

    def test_predict_returns_s0(self):
        s0 = np.ones((10, 10, 10), dtype="float32") * 42.0
        model = eddymotion.TrivialB0Model(S0=s0)
        result = model.predict()
        np.testing.assert_array_equal(result, s0)

    def test_no_s0_raises(self):
        with pytest.raises(ValueError, match="S0 must be provided"):
            eddymotion.TrivialB0Model()


class TestSortDwDataIndices:
    """Tests for _sort_dwdata_indices."""

    def test_length(self):
        indices = eddymotion._sort_dwdata_indices(seed=42, dwi_vol_count=10)
        assert len(indices) == 10

    def test_permutation(self):
        indices = eddymotion._sort_dwdata_indices(seed=42, dwi_vol_count=10)
        assert set(indices) == set(range(10))

    def test_deterministic(self):
        indices1 = eddymotion._sort_dwdata_indices(seed=42, dwi_vol_count=10)
        indices2 = eddymotion._sort_dwdata_indices(seed=42, dwi_vol_count=10)
        np.testing.assert_array_equal(indices1, indices2)

    def test_none_seed(self):
        indices = eddymotion._sort_dwdata_indices(seed=None, dwi_vol_count=10)
        assert len(indices) == 10


class TestAdvancedClip:
    """Tests for _advanced_clip helper."""

    def test_output_range(self):
        data = np.random.rand(10, 10, 10).astype("float32") * 1000
        result = eddymotion._advanced_clip(data, dtype="float32")
        assert result.min() >= 0
        assert result.max() <= 1.0

    def test_int16_cast(self):
        data = np.random.rand(10, 10, 10).astype("float32") * 1000
        result = eddymotion._advanced_clip(data, dtype="int16")
        assert result.dtype == np.int16
        assert result.min() >= 0
        assert result.max() <= 255

    def test_invert(self):
        data = np.random.rand(10, 10, 10).astype("float32") * 1000
        result = eddymotion._advanced_clip(data, invert=True, dtype="float32")
        # Inverted data: high values become low and vice versa
        assert result.min() >= 0.0
        assert result.max() <= 1.0


class TestBuildStages:
    """Tests for _build_stages helper."""

    def test_b0_stages(self):
        stages = eddymotion._build_stages(
            reg_target_type="b0",
            i_iter=0,
            fixed="/tmp/fixed.nii.gz",
            moving="/tmp/moving.nii.gz",
        )
        assert len(stages) == 2
        for stage in stages:
            assert "transform" in stage
            assert "metric" in stage
            assert "convergence" in stage
            assert "smoothing_sigmas" in stage
            assert "shrink_factors" in stage

    def test_dwi_l0_stages(self):
        stages = eddymotion._build_stages(
            reg_target_type="dwi",
            i_iter=0,
            fixed="/tmp/fixed.nii.gz",
            moving="/tmp/moving.nii.gz",
        )
        assert len(stages) == 2

    def test_dwi_l1_stages(self):
        stages = eddymotion._build_stages(
            reg_target_type="dwi",
            i_iter=1,
            fixed="/tmp/fixed.nii.gz",
            moving="/tmp/moving.nii.gz",
        )
        assert len(stages) == 2
