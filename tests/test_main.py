"""Tests for server.main — FastAPI endpoint integration tests."""

import pytest
from fastapi.testclient import TestClient

from server import anomalies, chaos
from server.main import app
from server.schemas import ChaosMode


@pytest.fixture(autouse=True)
def _reset_state():
    """Disable chaos and clear anomalies before and after each test."""
    chaos.disable()
    anomalies.clear()
    yield
    chaos.disable()
    anomalies.clear()


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
        assert "error_rate" in body

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
        assert body["endpoint"] == "/checkout"
        assert "latency_ms" in body
        assert "error_rate" in body

    def test_degraded_response_has_none_fields(self, client: TestClient):
        chaos.set_config(chaos.ChaosConfig(mode=ChaosMode.DEGRADED))
        resp = client.get("/checkout")
        assert resp.status_code == 200
        body = resp.json()
        assert body["order_id"] is None
        assert body["total"] is None
        assert body["status"] == "degraded"

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
        assert "message" in body
        assert "errors" in body["message"]
        assert chaos.get_config().mode == ChaosMode.ERRORS
        assert chaos.get_config().error_rate == 0.8

    def test_disable(self, client: TestClient):
        chaos.set_config(chaos.ChaosConfig(mode=ChaosMode.ERRORS))
        resp = client.post("/chaos/disable")
        assert resp.status_code == 200
        assert "message" in resp.json()
        assert chaos.get_config().mode == ChaosMode.OFF

    def test_status(self, client: TestClient):
        resp = client.get("/chaos/status")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is False
        assert body["mode"] is None


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


# ── Anomalies endpoint ──────────────────────────────────────────────


class TestAnomaliesEndpoint:
    def test_empty_when_no_chaos(self, client: TestClient):
        client.get("/health")
        resp = client.get("/anomalies")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_records_anomalies_on_error(self, client: TestClient):
        chaos.set_config(chaos.ChaosConfig(mode=ChaosMode.ERRORS, error_rate=1.0))
        client.get("/health")  # will 500
        resp = client.get("/anomalies")
        assert resp.status_code == 200
        records = resp.json()
        assert len(records) >= 1
        assert records[0]["endpoint"] == "/health"
        assert records[0]["recommended_action"] in ("REROUTE", "ALERT", "WAIT")

    def test_records_anomalies_on_degraded(self, client: TestClient):
        chaos.set_config(chaos.ChaosConfig(mode=ChaosMode.DEGRADED))
        client.get("/checkout")
        resp = client.get("/anomalies")
        assert resp.status_code == 200
        records = resp.json()
        assert len(records) >= 1
        assert records[0]["is_degraded"] is True


# ── Stats endpoint ───────────────────────────────────────────────────


class TestStatsEndpoint:
    def test_empty_stats(self, client: TestClient):
        resp = client.get("/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["totalIncidents"] == 0
        assert body["activeIncidents"] == 0
        assert body["apisMonitored"] == 0

    def test_stats_after_requests(self, client: TestClient):
        client.get("/health")
        client.get("/checkout")
        resp = client.get("/stats")
        body = resp.json()
        assert body["apisMonitored"] == 2

    def test_stats_count_anomalies(self, client: TestClient):
        chaos.set_config(chaos.ChaosConfig(mode=ChaosMode.ERRORS, error_rate=1.0))
        client.get("/health")
        resp = client.get("/stats")
        body = resp.json()
        assert body["totalIncidents"] >= 1


# ── Metrics history endpoint ────────────────────────────────────────


class TestMetricsHistoryEndpoint:
    def test_empty_when_no_requests(self, client: TestClient):
        resp = client.get("/metrics/history")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_returns_data_after_requests(self, client: TestClient):
        client.get("/health")
        client.get("/checkout")
        resp = client.get("/metrics/history")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        point = data[0]
        assert "time" in point
        assert "latency" in point
        assert "errorRate" in point
        assert "throughput" in point
        assert "uptime" in point


# ── Analyze endpoint ─────────────────────────────────────────────────


class TestAnalyzeEndpoint:
    def test_analyze_health(self, client: TestClient):
        resp = client.post("/analyze", json={"endpoint": "/health", "method": "GET"})
        assert resp.status_code == 200
        body = resp.json()
        assert body["endpoint"] == "/health"
        assert body["method"] == "GET"
        assert "status_code" in body
        assert "latency_ms" in body
