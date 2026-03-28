"""Tests for memory.auto_tune — adaptive THRESHOLD_K adjustment."""

import pytest

import agent.state as _state
from memory.auto_tune import _history, update


@pytest.fixture(autouse=True)
def _reset_auto_tune():
    _history.clear()
    original = _state.THRESHOLD_K
    _state.THRESHOLD_K = 2.5
    yield
    _history.clear()
    _state.THRESHOLD_K = original


class TestUpdateBasics:
    def test_ignores_invalid_action(self):
        update("INVALID")
        assert len(_history) == 0

    def test_accepts_valid_actions(self):
        for action in ("WAIT", "REROUTE", "ALERT"):
            update(action)
        assert len(_history) == 3

    def test_single_action_no_adjustment(self):
        update("WAIT")
        assert _state.THRESHOLD_K == 2.5


class TestThresholdAdjustment:
    def test_all_waits_increase_threshold(self):
        for _ in range(5):
            update("WAIT")
        assert _state.THRESHOLD_K > 2.5

    def test_all_reroutes_decrease_threshold(self):
        for _ in range(5):
            update("REROUTE")
        assert _state.THRESHOLD_K < 2.5

    def test_balanced_actions_minimal_change(self):
        for _ in range(3):
            update("WAIT")
        for _ in range(3):
            update("REROUTE")
        # With balanced WAIT/REROUTE, threshold should stay near original
        assert abs(_state.THRESHOLD_K - 2.5) < 0.5


class TestThresholdBounds:
    def test_never_drops_below_minimum(self):
        _state.THRESHOLD_K = 1.5
        for _ in range(100):
            update("REROUTE")
        assert _state.THRESHOLD_K >= 1.5

    def test_never_exceeds_maximum(self):
        _state.THRESHOLD_K = 5.0
        for _ in range(100):
            update("WAIT")
        assert _state.THRESHOLD_K <= 5.0


class TestHistoryWindow:
    def test_history_bounded_by_window_size(self):
        for _ in range(50):
            update("WAIT")
        assert len(_history) <= 10
