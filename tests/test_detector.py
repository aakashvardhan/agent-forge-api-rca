"""Tests for agent.detector — anomaly detection via z-score and thresholds."""

from datetime import datetime, timezone, timedelta

import pytest

import agent.state as _state
from agent.detector import _windows, _z_score, _prune, check
from server.schemas import NormalizedEvent


def _make_event(
    endpoint: str = "/health",
    latency_ms: float = 50.0,
    status_code: int = 200,
    error_rate_1m: float = 0.0,
    is_degraded: bool = False,
    error_detail: str | None = None,
    ts_offset_seconds: float = 0.0,
) -> NormalizedEvent:
    return NormalizedEvent(
        endpoint=endpoint,
        timestamp=datetime.now(timezone.utc) + timedelta(seconds=ts_offset_seconds),
        latency_ms=latency_ms,
        status_code=status_code,
        error_rate_1m=error_rate_1m,
        is_degraded=is_degraded,
        error_detail=error_detail,
        source="poller",
    )


@pytest.fixture(autouse=True)
def _reset_detector():
    """Clear sliding windows and reset threshold before each test."""
    _windows.clear()
    original_k = _state.THRESHOLD_K
    _state.THRESHOLD_K = 2.5
    yield
    _windows.clear()
    _state.THRESHOLD_K = original_k


class TestZScore:
    def test_empty_window_returns_zero(self):
        from collections import deque
        assert _z_score(100.0, deque()) == 0.0

    def test_single_element_returns_zero(self):
        from collections import deque
        window = deque([(datetime.now(timezone.utc), 50.0)])
        assert _z_score(50.0, window) == 0.0

    def test_identical_values_returns_zero(self):
        from collections import deque
        now = datetime.now(timezone.utc)
        window = deque([(now, 10.0), (now, 10.0), (now, 10.0)])
        assert _z_score(10.0, window) == 0.0

    def test_outlier_produces_high_z(self):
        from collections import deque
        now = datetime.now(timezone.utc)
        window = deque([(now, 10.0 + i * 0.1) for i in range(20)])
        z = _z_score(100.0, window)
        assert z > 3.0


class TestPrune:
    def test_removes_old_entries(self):
        from collections import deque
        now = datetime.now(timezone.utc)
        window = deque([
            (now - timedelta(seconds=120), 10.0),
            (now - timedelta(seconds=90), 10.0),
            (now, 10.0),
        ])
        _prune(window, now)
        assert len(window) == 1

    def test_keeps_recent_entries(self):
        from collections import deque
        now = datetime.now(timezone.utc)
        window = deque([
            (now - timedelta(seconds=30), 10.0),
            (now - timedelta(seconds=10), 20.0),
            (now, 30.0),
        ])
        _prune(window, now)
        assert len(window) == 3


class TestCheckNormal:
    def test_single_normal_event_returns_none(self):
        event = _make_event(latency_ms=50.0)
        result = check(event)
        assert result is None

    def test_consistent_latency_returns_none(self):
        for _ in range(10):
            event = _make_event(latency_ms=50.0)
            result = check(event)
        assert result is None


class TestCheckAnomalousHighErrorRate:
    def test_high_error_rate_triggers_anomaly(self):
        event = _make_event(error_rate_1m=0.5)
        result = check(event)
        assert result is not None
        assert result["error_rate_1m"] == 0.5
        assert result["endpoint"] == "/health"

    def test_borderline_error_rate_no_anomaly(self):
        event = _make_event(error_rate_1m=0.05)
        result = check(event)
        assert result is None


class TestCheckAnomalousDegraded:
    def test_degraded_flag_triggers_anomaly(self):
        event = _make_event(is_degraded=True)
        result = check(event)
        assert result is not None
        assert result["is_degraded"] is True

    def test_not_degraded_no_anomaly(self):
        event = _make_event(is_degraded=False)
        result = check(event)
        assert result is None


class TestCheckAnomalousLatencySpike:
    def test_latency_spike_after_baseline(self):
        _state.THRESHOLD_K = 2.0
        for i in range(20):
            check(_make_event(latency_ms=50.0 + i * 0.5))

        spike_event = _make_event(latency_ms=5000.0)
        result = check(spike_event)
        assert result is not None
        assert result["z_score"] > 2.0
        assert result["latency_ms"] == 5000.0


class TestCheckSymptomsShape:
    def test_symptoms_dict_has_all_keys(self):
        event = _make_event(
            error_rate_1m=0.5,
            status_code=500,
            error_detail="server error",
        )
        result = check(event)
        assert result is not None
        expected_keys = {
            "endpoint", "z_score", "latency_ms", "error_rate_1m",
            "is_degraded", "status_code", "error_detail",
        }
        assert set(result.keys()) == expected_keys


class TestCheckEndpointIsolation:
    def test_separate_windows_per_endpoint(self):
        for _ in range(20):
            check(_make_event(endpoint="/health", latency_ms=50.0))

        spike = _make_event(endpoint="/checkout", latency_ms=5000.0)
        result = check(spike)
        # /checkout has no baseline yet, so z-score is 0 — not anomalous via z-score
        # But it should still be None since error_rate is 0 and not degraded
        assert result is None
