"""Tests for ingestion.poller — HTTP polling and degradation detection."""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from ingestion.poller import DEGRADATION_RULES, Poller
from server.schemas import NormalizedEvent


# ── Degradation rules ───────────────────────────────────────────────


class TestDegradationRules:
    def test_checkout_rules_exist(self):
        rules = DEGRADATION_RULES["/checkout"]
        assert "order_id" in rules["required"]
        assert "total" in rules["required"]

    def test_health_rules_exist(self):
        rules = DEGRADATION_RULES["/health"]
        assert "status" in rules["required"]
        assert rules["degraded_values"]["status"] == "degraded"


# ── Poller construction ─────────────────────────────────────────────


class TestPollerInit:
    def test_defaults(self):
        poller = Poller()
        assert poller.base_url == "http://localhost:8000"
        assert poller.interval == 2.0
        assert set(poller._endpoints) == {"/checkout", "/health"}
        assert poller._running is False

    def test_trailing_slash_stripped(self):
        poller = Poller(base_url="http://example.com/")
        assert poller.base_url == "http://example.com"


# ── _check_degraded (static method, no network) ─────────────────────


class TestCheckDegraded:
    def _fake_response(self, json_body: dict) -> httpx.Response:
        """Build a minimal httpx.Response with a JSON body."""
        resp = httpx.Response(200, json=json_body)
        return resp

    def test_healthy_checkout(self):
        resp = self._fake_response({"order_id": "abc", "total": 10.0})
        assert Poller._check_degraded("/checkout", resp) is False

    def test_degraded_checkout_missing_order_id(self):
        resp = self._fake_response({"order_id": None, "total": 10.0})
        assert Poller._check_degraded("/checkout", resp) is True

    def test_degraded_checkout_missing_total(self):
        resp = self._fake_response({"order_id": "abc", "total": None})
        assert Poller._check_degraded("/checkout", resp) is True

    def test_healthy_health(self):
        resp = self._fake_response({"status": "ok", "endpoint": "/health"})
        assert Poller._check_degraded("/health", resp) is False

    def test_degraded_health_status(self):
        resp = self._fake_response({"status": "degraded", "endpoint": "/health"})
        assert Poller._check_degraded("/health", resp) is True

    def test_degraded_health_missing_field(self):
        resp = self._fake_response({"endpoint": "/health"})
        assert Poller._check_degraded("/health", resp) is True

    def test_unknown_endpoint_returns_false(self):
        resp = self._fake_response({"anything": True})
        assert Poller._check_degraded("/unknown", resp) is False

    def test_non_json_body_returns_true(self):
        resp = httpx.Response(200, text="not json")
        assert Poller._check_degraded("/health", resp) is True


# ── _extract_error_detail (static method) ────────────────────────────


class TestExtractErrorDetail:
    def test_json_detail(self):
        resp = httpx.Response(500, json={"detail": "bad stuff"})
        assert Poller._extract_error_detail(resp) == "bad stuff"

    def test_json_no_detail_key(self):
        resp = httpx.Response(500, json={"error": "something"})
        assert Poller._extract_error_detail(resp) is None

    def test_plain_text_fallback(self):
        resp = httpx.Response(500, text="raw error text")
        assert Poller._extract_error_detail(resp) == "raw error text"

    def test_empty_body(self):
        resp = httpx.Response(500, text="")
        assert Poller._extract_error_detail(resp) is None


# ── _poll_endpoint (async, uses transport mock) ──────────────────────


class TestPollEndpoint:
    @pytest.mark.asyncio
    async def test_successful_poll_emits_event(self):
        collected: list[NormalizedEvent] = []
        callback = AsyncMock(side_effect=lambda e: collected.append(e))

        handler = httpx.MockTransport(
            lambda req: httpx.Response(
                200, json={"status": "ok", "endpoint": "/health"}
            )
        )
        poller = Poller(on_event=callback)
        async with httpx.AsyncClient(transport=handler) as client:
            await poller._poll_endpoint(client, "/health")

        assert len(collected) == 1
        event = collected[0]
        assert event.status_code == 200
        assert event.is_degraded is False
        assert event.error_detail is None
        assert event.source == "poller"

    @pytest.mark.asyncio
    async def test_server_error_poll(self):
        collected: list[NormalizedEvent] = []
        callback = AsyncMock(side_effect=lambda e: collected.append(e))

        handler = httpx.MockTransport(
            lambda req: httpx.Response(
                500, json={"detail": "Injected server error"}
            )
        )
        poller = Poller(on_event=callback)
        async with httpx.AsyncClient(transport=handler) as client:
            await poller._poll_endpoint(client, "/health")

        event = collected[0]
        assert event.status_code == 500
        assert event.error_detail == "Injected server error"

    @pytest.mark.asyncio
    async def test_degraded_response_detected(self):
        collected: list[NormalizedEvent] = []
        callback = AsyncMock(side_effect=lambda e: collected.append(e))

        handler = httpx.MockTransport(
            lambda req: httpx.Response(
                200, json={"status": "degraded", "endpoint": "/health"}
            )
        )
        poller = Poller(on_event=callback)
        async with httpx.AsyncClient(transport=handler) as client:
            await poller._poll_endpoint(client, "/health")

        event = collected[0]
        assert event.status_code == 200
        assert event.is_degraded is True

    @pytest.mark.asyncio
    async def test_timeout_sets_status_zero(self):
        collected: list[NormalizedEvent] = []
        callback = AsyncMock(side_effect=lambda e: collected.append(e))

        def raise_timeout(req):
            raise httpx.ReadTimeout("timed out")

        handler = httpx.MockTransport(raise_timeout)
        poller = Poller(on_event=callback)
        async with httpx.AsyncClient(transport=handler) as client:
            await poller._poll_endpoint(client, "/health")

        event = collected[0]
        assert event.status_code == 0
        assert event.error_detail == "Request timed out"

    @pytest.mark.asyncio
    async def test_connection_error(self):
        collected: list[NormalizedEvent] = []
        callback = AsyncMock(side_effect=lambda e: collected.append(e))

        def raise_conn_error(req):
            raise httpx.ConnectError("Connection refused")

        handler = httpx.MockTransport(raise_conn_error)
        poller = Poller(on_event=callback)
        async with httpx.AsyncClient(transport=handler) as client:
            await poller._poll_endpoint(client, "/health")

        event = collected[0]
        assert event.status_code == 0
        assert "Connection refused" in event.error_detail

    @pytest.mark.asyncio
    async def test_error_rate_accumulates(self):
        collected: list[NormalizedEvent] = []
        callback = AsyncMock(side_effect=lambda e: collected.append(e))

        handler = httpx.MockTransport(
            lambda req: httpx.Response(500, json={"detail": "fail"})
        )
        poller = Poller(on_event=callback)
        async with httpx.AsyncClient(transport=handler) as client:
            await poller._poll_endpoint(client, "/health")
            await poller._poll_endpoint(client, "/health")
            await poller._poll_endpoint(client, "/health")

        assert collected[-1].error_rate_1m == 1.0

    @pytest.mark.asyncio
    async def test_no_callback_does_not_crash(self):
        """Poller with no on_event callback should poll without errors."""
        handler = httpx.MockTransport(
            lambda req: httpx.Response(200, json={"status": "ok", "endpoint": "/health"})
        )
        poller = Poller(on_event=None)
        async with httpx.AsyncClient(transport=handler) as client:
            await poller._poll_endpoint(client, "/health")


# ── start / stop lifecycle ───────────────────────────────────────────


class TestPollerLifecycle:
    def test_stop_sets_running_false(self):
        poller = Poller()
        poller._running = True
        poller.stop()
        assert poller._running is False

    @pytest.mark.asyncio
    async def test_start_sets_running_true_then_stop(self):
        poller = Poller(interval=0.05)

        async def stop_after_brief_delay():
            await asyncio.sleep(0.1)
            poller.stop()

        asyncio.create_task(stop_after_brief_delay())
        # Monkey-patch _poll_endpoint to avoid real HTTP calls
        poller._poll_endpoint = AsyncMock()
        await poller.start()
        assert poller._running is False
