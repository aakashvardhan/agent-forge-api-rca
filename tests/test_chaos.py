"""Tests for server.chaos — chaos injection engine."""

from unittest.mock import AsyncMock, patch

import pytest

from server.chaos import (
    disable,
    get_config,
    is_degraded,
    maybe_inject_latency,
    set_config,
    should_return_error,
)
from server.schemas import ChaosConfig, ChaosMode


@pytest.fixture(autouse=True)
def _reset_chaos():
    """Ensure chaos is disabled before and after every test."""
    disable()
    yield
    disable()


class TestGetSetConfig:
    def test_default_is_off(self):
        cfg = get_config()
        assert cfg.mode == ChaosMode.OFF

    def test_set_returns_same_config(self):
        new_cfg = ChaosConfig(mode=ChaosMode.LATENCY, latency_min=1.0)
        result = set_config(new_cfg)
        assert result is new_cfg
        assert get_config() is new_cfg

    def test_disable_resets_to_off(self):
        set_config(ChaosConfig(mode=ChaosMode.ERRORS))
        disable()
        assert get_config().mode == ChaosMode.OFF


class TestIsDegraded:
    def test_false_when_off(self):
        assert is_degraded() is False

    def test_true_when_degraded_mode(self):
        set_config(ChaosConfig(mode=ChaosMode.DEGRADED))
        assert is_degraded() is True

    def test_false_for_other_modes(self):
        for mode in (ChaosMode.LATENCY, ChaosMode.ERRORS, ChaosMode.OFF):
            set_config(ChaosConfig(mode=mode))
            assert is_degraded() is False


class TestShouldReturnError:
    def test_false_when_off(self):
        assert should_return_error() is False

    def test_always_true_when_rate_1(self):
        set_config(ChaosConfig(mode=ChaosMode.ERRORS, error_rate=1.0))
        assert should_return_error() is True

    def test_always_false_when_rate_0(self):
        set_config(ChaosConfig(mode=ChaosMode.ERRORS, error_rate=0.0))
        assert should_return_error() is False

    @patch("server.chaos.random.random", return_value=0.3)
    def test_below_threshold_returns_true(self, _mock_random):
        set_config(ChaosConfig(mode=ChaosMode.ERRORS, error_rate=0.5))
        assert should_return_error() is True

    @patch("server.chaos.random.random", return_value=0.7)
    def test_above_threshold_returns_false(self, _mock_random):
        set_config(ChaosConfig(mode=ChaosMode.ERRORS, error_rate=0.5))
        assert should_return_error() is False


class TestMaybeInjectLatency:
    @pytest.mark.asyncio
    async def test_no_delay_when_off(self):
        result = await maybe_inject_latency()
        assert result == 0.0

    @pytest.mark.asyncio
    @patch("server.chaos.asyncio.sleep", new_callable=AsyncMock)
    @patch("server.chaos.random.uniform", return_value=0.01)
    async def test_injects_latency_when_active(self, _mock_uniform, mock_sleep):
        set_config(ChaosConfig(mode=ChaosMode.LATENCY, latency_min=0.01, latency_max=0.02))
        result = await maybe_inject_latency()
        mock_sleep.assert_awaited_once_with(0.01)
        assert result == pytest.approx(10.0)  # 0.01s * 1000 = 10ms

    @pytest.mark.asyncio
    async def test_no_delay_in_errors_mode(self):
        set_config(ChaosConfig(mode=ChaosMode.ERRORS))
        result = await maybe_inject_latency()
        assert result == 0.0
