"""Tests for memory.case_store — past incident storage and similarity lookup."""

import pytest

import agent.state as _state
from memory.case_store import _cases, get_similar, save


@pytest.fixture(autouse=True)
def _reset_store():
    _cases.clear()
    original_k = _state.THRESHOLD_K
    _state.THRESHOLD_K = 2.5
    yield
    _cases.clear()
    _state.THRESHOLD_K = original_k


def _symptoms(
    endpoint="/health",
    z_score=3.0,
    error_rate_1m=0.5,
    is_degraded=False,
) -> dict:
    return {
        "endpoint": endpoint,
        "z_score": z_score,
        "error_rate_1m": error_rate_1m,
        "is_degraded": is_degraded,
        "latency_ms": 100.0,
        "status_code": 500,
        "error_detail": None,
    }


class TestSave:
    def test_appends_case(self):
        save(_symptoms(), {"diagnosis": "overload", "action": "REROUTE"})
        assert len(_cases) == 1
        assert _cases[0]["endpoint"] == "/health"
        assert _cases[0]["action"] == "REROUTE"

    def test_case_has_timestamp(self):
        save(_symptoms(), {"diagnosis": "x", "action": "WAIT"})
        assert "timestamp" in _cases[0]

    def test_multiple_saves_accumulate(self):
        for _ in range(5):
            save(_symptoms(), {"diagnosis": "x", "action": "ALERT"})
        assert len(_cases) == 5


class TestGetSimilar:
    def test_empty_store_returns_empty(self):
        result = get_similar(_symptoms())
        assert result == []

    def test_returns_matching_endpoint(self):
        save(_symptoms(endpoint="/health"), {"diagnosis": "x", "action": "REROUTE"})
        save(_symptoms(endpoint="/checkout"), {"diagnosis": "y", "action": "ALERT"})

        result = get_similar(_symptoms(endpoint="/health"))
        assert len(result) == 1
        assert result[0]["endpoint"] == "/health"

    def test_respects_k_limit(self):
        for i in range(10):
            save(
                _symptoms(z_score=3.0 + i, error_rate_1m=0.5),
                {"diagnosis": f"case-{i}", "action": "REROUTE"},
            )

        result = get_similar(_symptoms(), k=3)
        assert len(result) == 3

    def test_scores_by_symptom_severity(self):
        save(
            _symptoms(z_score=0.5, error_rate_1m=0.01, is_degraded=False),
            {"diagnosis": "mild", "action": "WAIT"},
        )
        save(
            _symptoms(z_score=5.0, error_rate_1m=0.9, is_degraded=True),
            {"diagnosis": "severe", "action": "REROUTE"},
        )

        result = get_similar(_symptoms())
        assert result[0]["diagnosis"] == "severe"

    def test_excludes_zero_score_cases(self):
        save(
            _symptoms(z_score=0.5, error_rate_1m=0.01, is_degraded=False),
            {"diagnosis": "benign", "action": "WAIT"},
        )

        result = get_similar(_symptoms())
        assert result == []
