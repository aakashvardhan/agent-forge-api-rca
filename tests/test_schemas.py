"""Tests for server.schemas — Pydantic models and validators."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from server.schemas import (
    ChaosConfig,
    ChaosMode,
    CheckoutResponse,
    HealthResponse,
    NormalizedEvent,
)


# ── ChaosMode enum ──────────────────────────────────────────────────


class TestChaosMode:
    def test_values(self):
        assert ChaosMode.LATENCY.value == "latency"
        assert ChaosMode.ERRORS.value == "errors"
        assert ChaosMode.DEGRADED.value == "degraded"
        assert ChaosMode.OFF.value == "off"

    def test_from_string(self):
        assert ChaosMode("latency") is ChaosMode.LATENCY


# ── ChaosConfig ─────────────────────────────────────────────────────


class TestChaosConfig:
    def test_defaults(self):
        cfg = ChaosConfig()
        assert cfg.mode == ChaosMode.LATENCY
        assert cfg.error_rate == 0.5
        assert cfg.latency_min == 2000.0
        assert cfg.latency_max == 5000.0

    def test_custom_values(self):
        cfg = ChaosConfig(
            mode=ChaosMode.ERRORS,
            error_rate=0.8,
            latency_min=1.0,
            latency_max=3.0,
        )
        assert cfg.mode == ChaosMode.ERRORS
        assert cfg.error_rate == 0.8

    def test_error_rate_bounds(self):
        with pytest.raises(ValidationError):
            ChaosConfig(error_rate=-0.1)
        with pytest.raises(ValidationError):
            ChaosConfig(error_rate=1.1)

    def test_latency_min_non_negative(self):
        with pytest.raises(ValidationError):
            ChaosConfig(latency_min=-1.0)

    def test_latency_max_non_negative(self):
        with pytest.raises(ValidationError):
            ChaosConfig(latency_max=-0.5)


# ── HealthResponse ──────────────────────────────────────────────────


class TestHealthResponse:
    def test_basic(self):
        resp = HealthResponse(endpoint="/health", latency_ms=12.5)
        assert resp.status == "ok"
        assert resp.endpoint == "/health"
        assert resp.latency_ms == 12.5
        assert isinstance(resp.timestamp, datetime)

    def test_degraded_status(self):
        resp = HealthResponse(status="degraded", endpoint="/health", latency_ms=0.0)
        assert resp.status == "degraded"


# ── CheckoutResponse ────────────────────────────────────────────────


class TestCheckoutResponse:
    def test_full_response(self):
        resp = CheckoutResponse(order_id="abc123", total=99.99)
        assert resp.order_id == "abc123"
        assert resp.total == 99.99
        assert resp.status == "confirmed"

    def test_degraded_response_allows_none(self):
        resp = CheckoutResponse(order_id=None, total=None)
        assert resp.order_id is None
        assert resp.total is None
        assert resp.status == "confirmed"


# ── NormalizedEvent ─────────────────────────────────────────────────


class TestNormalizedEvent:
    def _make_event(self, **overrides) -> NormalizedEvent:
        defaults = {
            "endpoint": "/health",
            "timestamp": datetime.now(timezone.utc),
            "latency_ms": 50.0,
            "status_code": 200,
            "source": "poller",
        }
        defaults.update(overrides)
        return NormalizedEvent(**defaults)

    def test_happy_path(self):
        event = self._make_event()
        assert event.endpoint == "/health"
        assert event.status_code == 200
        assert event.is_degraded is False
        assert event.error_detail is None
        assert event.schema_version == 1
        assert len(event.event_id) == 32  # uuid hex

    def test_event_id_auto_generated(self):
        e1 = self._make_event()
        e2 = self._make_event()
        assert e1.event_id != e2.event_id

    def test_degraded_with_success_status(self):
        event = self._make_event(status_code=200, is_degraded=True)
        assert event.is_degraded is True

    def test_degraded_with_error_status_raises(self):
        with pytest.raises(ValidationError, match="is_degraded=True is invalid"):
            self._make_event(status_code=500, is_degraded=True)

    def test_error_detail_cleared_on_success(self):
        event = self._make_event(
            status_code=200,
            error_detail="should be cleared",
        )
        assert event.error_detail is None

    def test_error_detail_kept_on_failure(self):
        event = self._make_event(
            status_code=500,
            error_detail="internal server error",
        )
        assert event.error_detail == "internal server error"

    def test_error_detail_kept_on_status_zero(self):
        event = self._make_event(
            status_code=0,
            error_detail="Request timed out",
        )
        assert event.error_detail == "Request timed out"

    def test_error_rate_bounds(self):
        with pytest.raises(ValidationError):
            self._make_event(error_rate_1m=-0.1)
        with pytest.raises(ValidationError):
            self._make_event(error_rate_1m=1.1)

    def test_valid_sources(self):
        for src in ("health_check", "nexla", "poller"):
            event = self._make_event(source=src)
            assert event.source == src

    def test_invalid_source_rejected(self):
        with pytest.raises(ValidationError):
            self._make_event(source="unknown_source")
