"""Tests for server.main — FastAPI endpoint integration tests."""

import pytest
from fastapi.testclient import TestClient

from server import chaos
from server.main import app
from server.schemas import ChaosMode


@pytest.fixture(autouse=True)
def _reset_chaos():
    """Disable chaos before and after each test."""
    chaos.disable()
    yield
    chaos.disable()


@pytest.fixture
def client():
    return TestClient(app)


# ── Health endpoint ─────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_returns_ok(self, client: TestClient):
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert body["endpoint"] == "/health"
        assert "latency_ms" in body

    def test_degraded_mode(self, client: TestClient):
        chaos.set_config(chaos.ChaosConfig(mode=ChaosMode.DEGRADED))
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "degraded"

    def test_error_mode(self, client: TestClient):
        chaos.set_config(
            chaos.ChaosConfig(mode=ChaosMode.ERRORS, error_rate=1.0)
        )
        resp = client.get("/health")
        assert resp.status_code == 500
        assert "Injected server error" in resp.json()["detail"]


# ── Checkout endpoint ───────────────────────────────────────────────


class TestCheckoutEndpoint:
    def test_returns_full_response(self, client: TestClient):
        resp = client.get("/checkout")
        assert resp.status_code == 200
        body = resp.json()
        assert body["order_id"] is not None
        assert body["total"] is not None
        assert body["status"] == "confirmed"

    def test_degraded_response_has_none_fields(self, client: TestClient):
        chaos.set_config(chaos.ChaosConfig(mode=ChaosMode.DEGRADED))
        resp = client.get("/checkout")
        assert resp.status_code == 200
        body = resp.json()
        assert body["order_id"] is None
        assert body["total"] is None

    def test_error_mode(self, client: TestClient):
        chaos.set_config(
            chaos.ChaosConfig(mode=ChaosMode.ERRORS, error_rate=1.0)
        )
        resp = client.get("/checkout")
        assert resp.status_code == 500
        assert "Checkout processing failed" in resp.json()["detail"]


# ── Chaos control endpoints ─────────────────────────────────────────


class TestChaosControlEndpoints:
    def test_enable(self, client: TestClient):
        resp = client.post(
            "/chaos/enable",
            json={"mode": "errors", "error_rate": 0.8},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "chaos_enabled"
        assert body["config"]["mode"] == "errors"
        assert body["config"]["error_rate"] == 0.8

    def test_disable(self, client: TestClient):
        chaos.set_config(chaos.ChaosConfig(mode=ChaosMode.ERRORS))
        resp = client.post("/chaos/disable")
        assert resp.status_code == 200
        assert resp.json()["status"] == "chaos_disabled"
        assert chaos.get_config().mode == ChaosMode.OFF

    def test_status(self, client: TestClient):
        resp = client.get("/chaos/status")
        assert resp.status_code == 200
        assert resp.json()["config"]["mode"] == "off"


# ── Metrics endpoint ────────────────────────────────────────────────


class TestMetricsEndpoint:
    def test_metrics_when_off(self, client: TestClient):
        resp = client.get("/metrics")
        assert resp.status_code == 200
        body = resp.json()
        assert body["chaos_active"] is False
        assert body["chaos_mode"] == "off"
        assert "timestamp" in body

    def test_metrics_when_active(self, client: TestClient):
        chaos.set_config(chaos.ChaosConfig(mode=ChaosMode.LATENCY))
        resp = client.get("/metrics")
        body = resp.json()
        assert body["chaos_active"] is True
        assert body["chaos_mode"] == "latency"
