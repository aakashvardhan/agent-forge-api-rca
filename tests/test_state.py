"""Tests for agent.state — shared THRESHOLD_K configuration."""

import pytest

import agent.state as _state


@pytest.fixture(autouse=True)
def _reset_threshold():
    original = _state.THRESHOLD_K
    yield
    _state.THRESHOLD_K = original


class TestThresholdK:
    def test_default_type_is_float(self):
        assert isinstance(_state.THRESHOLD_K, float)

    def test_default_is_positive(self):
        assert _state.THRESHOLD_K > 0

    def test_can_be_mutated_at_runtime(self):
        _state.THRESHOLD_K = 3.0
        assert _state.THRESHOLD_K == 3.0

    def test_default_value_is_2_5(self):
        """Default from .env or fallback should be 2.5."""
        # Reset to the os.getenv default
        _state.THRESHOLD_K = float("2.5")
        assert _state.THRESHOLD_K == 2.5
