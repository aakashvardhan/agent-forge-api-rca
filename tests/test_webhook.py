"""Tests for ingestion.webhook — Nexla webhook receiver."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from ingestion.webhook import WebhookReceiver
from server.schemas import NormalizedEvent


def _sample_event_payload(**overrides) -> dict:
    """Build a valid NormalizedEvent JSON payload for POST /ingest."""
    defaults = {
        "endpoint": "/health",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_ms": 42.0,
        "status_code": 200,
        "error_rate_1m": 0.0,
        "is_degraded": False,
        "error_detail": None,
        "source": "nexla",
    }
    defaults.update(overrides)
    return defaults


# ── Construction ─────────────────────────────────────────────────────


class TestWebhookReceiverInit:
    def test_default_counts_zero(self):
        receiver = WebhookReceiver()
        assert receiver._event_count == 0
        assert receiver._error_count == 0

    def test_callback_stored(self):
        cb = AsyncMock()
        receiver = WebhookReceiver(on_event=cb)
        assert receiver._callback is cb

    def test_no_callback_by_default(self):
        receiver = WebhookReceiver()
        assert receiver._callback is None

    def test_app_is_created(self):
        receiver = WebhookReceiver()
        assert receiver._app is not None


# ── POST /ingest ─────────────────────────────────────────────────────


class TestIngestEndpoint:
    def test_successful_ingest(self):
        cb = AsyncMock()
        receiver = WebhookReceiver(on_event=cb)
        client = TestClient(receiver._app)

        payload = _sample_event_payload()
        resp = client.post("/ingest", json=payload)

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "received"
        assert "event_id" in body
        cb.assert_awaited_once()
        assert receiver._event_count == 1
        assert receiver._error_count == 0

    def test_callback_receives_normalized_event(self):
        captured = []
        async def capture(event):
            captured.append(event)

        receiver = WebhookReceiver(on_event=capture)
        client = TestClient(receiver._app)

        payload = _sample_event_payload(endpoint="/checkout", status_code=200)
        client.post("/ingest", json=payload)

        assert len(captured) == 1
        assert isinstance(captured[0], NormalizedEvent)
        assert captured[0].endpoint == "/checkout"
        assert captured[0].source == "nexla"

    def test_503_when_no_callback(self):
        receiver = WebhookReceiver(on_event=None)
        client = TestClient(receiver._app)

        resp = client.post("/ingest", json=_sample_event_payload())

        assert resp.status_code == 503
        assert "no callback registered" in resp.json()["detail"].lower()
        assert receiver._event_count == 0

    def test_500_when_callback_raises(self):
        cb = AsyncMock(side_effect=RuntimeError("agent crashed"))
        receiver = WebhookReceiver(on_event=cb)
        client = TestClient(receiver._app)

        resp = client.post("/ingest", json=_sample_event_payload())

        assert resp.status_code == 500
        body = resp.json()
        assert body["status"] == "callback_error"
        assert "agent crashed" in body["detail"]
        assert receiver._error_count == 1
        assert receiver._event_count == 0

    def test_invalid_payload_returns_422(self):
        receiver = WebhookReceiver(on_event=AsyncMock())
        client = TestClient(receiver._app)

        resp = client.post("/ingest", json={"bad": "data"})

        assert resp.status_code == 422

    def test_multiple_ingests_increment_count(self):
        cb = AsyncMock()
        receiver = WebhookReceiver(on_event=cb)
        client = TestClient(receiver._app)

        for _ in range(5):
            resp = client.post("/ingest", json=_sample_event_payload())
            assert resp.status_code == 200

        assert receiver._event_count == 5
        assert cb.await_count == 5

    def test_mixed_success_and_failure_counts(self):
        call_count = 0
        async def flaky_callback(event):
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0:
                raise RuntimeError("intermittent failure")

        receiver = WebhookReceiver(on_event=flaky_callback)
        client = TestClient(receiver._app)

        results = []
        for _ in range(4):
            resp = client.post("/ingest", json=_sample_event_payload())
            results.append(resp.status_code)

        assert results == [200, 500, 200, 500]
        assert receiver._event_count == 2
        assert receiver._error_count == 2


# ── GET /stats ───────────────────────────────────────────────────────


class TestStatsEndpoint:
    def test_initial_stats(self):
        receiver = WebhookReceiver(on_event=AsyncMock())
        client = TestClient(receiver._app)

        resp = client.get("/stats")
        assert resp.status_code == 200
        body = resp.json()
        assert body["events_received"] == 0
        assert body["callback_errors"] == 0
        assert body["callback_registered"] is True

    def test_callback_not_registered(self):
        receiver = WebhookReceiver(on_event=None)
        client = TestClient(receiver._app)

        body = client.get("/stats").json()
        assert body["callback_registered"] is False

    def test_stats_reflect_ingested_events(self):
        cb = AsyncMock()
        receiver = WebhookReceiver(on_event=cb)
        client = TestClient(receiver._app)

        client.post("/ingest", json=_sample_event_payload())
        client.post("/ingest", json=_sample_event_payload())

        body = client.get("/stats").json()
        assert body["events_received"] == 2
        assert body["callback_errors"] == 0

    def test_stats_reflect_errors(self):
        cb = AsyncMock(side_effect=ValueError("boom"))
        receiver = WebhookReceiver(on_event=cb)
        client = TestClient(receiver._app)

        client.post("/ingest", json=_sample_event_payload())

        body = client.get("/stats").json()
        assert body["events_received"] == 0
        assert body["callback_errors"] == 1


# ── GET /health ──────────────────────────────────────────────────────


class TestHealthEndpoint:
    def test_healthy_when_callback_registered(self):
        receiver = WebhookReceiver(on_event=AsyncMock())
        client = TestClient(receiver._app)

        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_503_when_no_callback(self):
        receiver = WebhookReceiver(on_event=None)
        client = TestClient(receiver._app)

        resp = client.get("/health")
        assert resp.status_code == 503
        assert "No callback" in resp.json()["detail"]
