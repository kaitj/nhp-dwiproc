import logging

import pytest

from nhp_dwiproc.app.lib import metadata


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
