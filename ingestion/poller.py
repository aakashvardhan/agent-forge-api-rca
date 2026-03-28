"""Fallback poller — direct HTTP polling when Nexla isn't available.

Hits the mock API on a fixed interval, computes a rolling error rate,
detects degraded responses via body inspection, and pushes
NormalizedEvent objects to a callback. Drop-in replacement for the
Nexla webhook path.

Usage:
    poller = Poller(
        base_url="http://localhost:8000",
        on_event=my_agent.ingest,   # async callable(NormalizedEvent)
        interval=2.0,
    )
    await poller.start()
"""

import asyncio
import logging
import time
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Awaitable

import httpx

from server.schemas import NormalizedEvent

logger = logging.getLogger(__name__)


# ── Per-endpoint degradation rules ───────────────────────────────────
# Two kinds of rules per endpoint:
#   "required"  → fields that MUST be non-None on a 2xx response
#   "degraded_values" → field:value pairs that explicitly signal degradation
#
# Add new endpoints here as the mock server grows.

DEGRADATION_RULES: dict[str, dict] = {
    "/checkout": {
        "required": ["order_id", "total"],
        "degraded_values": {},
    },
    "/health": {
        "required": ["status", "endpoint"],
        "degraded_values": {"status": "degraded"},
    },
}


class Poller:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        on_event: Callable[[NormalizedEvent], Awaitable[None]] | None = None,
        interval: float = 2.0,
        error_window: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.on_event = on_event
        self.interval = interval
        self._endpoints = list(DEGRADATION_RULES.keys())
        self._error_history: dict[str, deque] = {
            ep: deque(maxlen=error_window) for ep in self._endpoints
        }
        self._running = False

    async def start(self):
        """Start polling loop. Blocks until stop() is called."""
        self._running = True
        logger.info(
            "Poller started — base_url=%s, interval=%.1fs, endpoints=%s",
            self.base_url, self.interval, self._endpoints,
        )
        async with httpx.AsyncClient(timeout=10.0) as client:
            while self._running:
                tasks = [self._poll_endpoint(client, ep) for ep in self._endpoints]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for result in results:
                    if isinstance(result, Exception):
                        logger.error("Error polling endpoint: %s", result)
                await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False
        logger.info("Poller stopped")

    async def _poll_endpoint(self, client: httpx.AsyncClient, endpoint: str):
        url = f"{self.base_url}{endpoint}"
        start = time.perf_counter()

        resp: httpx.Response | None = None
        status_code = 0
        error_detail: str | None = None
        is_degraded = False

        try:
            resp = await client.get(url)
            latency_ms = (time.perf_counter() - start) * 1000
            status_code = resp.status_code

            # ── Extract error detail on failure ──
            if status_code >= 400:
                error_detail = self._extract_error_detail(resp)

            # ── Detect degraded responses on success ──
            if status_code < 400:
                is_degraded = self._check_degraded(endpoint, resp)

        except httpx.TimeoutException:
            latency_ms = (time.perf_counter() - start) * 1000
            status_code = 0
            error_detail = "Request timed out"
            logger.warning("Timeout polling %s (%.0fms)", url, latency_ms)

        except httpx.RequestError as exc:
            latency_ms = (time.perf_counter() - start) * 1000
            status_code = 0
            error_detail = str(exc)[:500]
            logger.warning("Connection error polling %s: %s", url, exc)

        # ── Update rolling error rate ──
        is_error = status_code >= 500 or status_code == 0
        history = self._error_history[endpoint]
        history.append(1.0 if is_error else 0.0)
        error_rate = sum(history) / len(history) if history else 0.0

        # ── Build and emit event ──
        event = NormalizedEvent(
            endpoint=endpoint,
            timestamp=datetime.now(timezone.utc),
            latency_ms=round(latency_ms, 2),
            status_code=status_code,
            error_rate_1m=round(error_rate, 3),
            is_degraded=is_degraded,
            error_detail=error_detail,
            source="poller",
        )

        if self.on_event:
            await self.on_event(event)

    # ── Private helpers ──────────────────────────────────────────────

    @staticmethod
    def _extract_error_detail(resp: httpx.Response) -> str | None:
        """Pull a short error message from a 4xx/5xx response."""
        try:
            body = resp.json()
            detail = body.get("detail", "")
            return str(detail)[:500] if detail else None
        except Exception:
            text = resp.text[:500] if resp.text else None
            return text

    @staticmethod
    def _check_degraded(endpoint: str, resp: httpx.Response) -> bool:
        """Check if a 2xx response signals degradation.

        Two checks per endpoint (both defined in DEGRADATION_RULES):
          1. Required fields — any None means degraded.
          2. Degraded values — a field matching a known-bad value
             (e.g. /health returning status="degraded") means degraded.

        Returns False for unknown endpoints (open-world safe).
        """
        rules = DEGRADATION_RULES.get(endpoint)
        if not rules:
            return False

        try:
            body = resp.json()
        except Exception:
            return True

        # Check 1: required fields present and non-None
        for field in rules.get("required", []):
            if body.get(field) is None:
                return True

        # Check 2: field values that explicitly signal degradation
        for field, bad_value in rules.get("degraded_values", {}).items():
            if body.get(field) == bad_value:
                return True

        return False