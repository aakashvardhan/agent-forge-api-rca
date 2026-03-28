"""AgentForge mock API server.

Two business endpoints (/health, /checkout) that behave normally
until you flip the chaos toggle.  The agent monitors these.

Run: uvicorn server.main:app --port 8000
"""

import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone

import httpx
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from server.schemas import (
    ChaosConfig,
    ChaosMode,
    CheckoutResponse,
    HealthResponse,
)
from server import anomalies, chaos

app = FastAPI(title="AgentForge Mock API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_EVENT_BUFFER = 100
_recent_events: deque[dict] = deque(maxlen=MAX_EVENT_BUFFER)

_SELF_BASE = os.getenv("AGENTFORGE_BASE_URL", "http://localhost:8000")


@app.middleware("http")
async def add_ngrok_compat_headers(request: Request, call_next):
    """Ensure responses carry headers that help bypass ngrok's
    free-tier interstitial and signal content type clearly."""
    response: Response = await call_next(request)
    response.headers["ngrok-skip-browser-warning"] = "true"
    return response


# ── Root endpoint (Nexla polls this by default) ──────────────────────


@app.get("/", tags=["api"])
async def root():
    """Landing endpoint. Returns server info so Nexla (and other
    tools) get a valid JSON response when polling the base URL."""
    cfg = chaos.get_config()
    return {
        "service": "agentforge-mock-api",
        "version": "0.1.0",
        "status": "degraded" if chaos.is_degraded() else "ok",
        "chaos_active": cfg.mode != ChaosMode.OFF,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": ["/health", "/checkout", "/data", "/metrics"],
    }


# ── Nexla-friendly data endpoint ────────────────────────────────────


@app.get("/data", tags=["api"])
async def data_feed():
    """Returns recent endpoint observations as a JSON array.

    Nexla auto-creates a Nexset when it can infer a schema from the
    response. A single flat object often isn't enough — this endpoint
    returns an array of recent event snapshots so schema inference
    succeeds on the first poll cycle.
    """
    live_samples = []
    for endpoint in ("/health", "/checkout"):
        start = time.perf_counter()
        latency_ms = round((time.perf_counter() - start) * 1000, 2)
        sample = {
            "endpoint": endpoint,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latency_ms": latency_ms,
            "status_code": 200,
            "error_rate_1m": 0.0,
            "is_degraded": chaos.is_degraded(),
            "chaos_mode": chaos.get_config().mode.value,
        }
        live_samples.append(sample)
        _recent_events.append(sample)

    return list(_recent_events) if _recent_events else live_samples


# ── Chaos control endpoints ─────────────────────────────────────────


@app.post("/chaos/enable", tags=["chaos"])
async def enable_chaos(config: ChaosConfig) -> dict:
    """Activate a failure mode. Hit this from your phone during the demo."""
    chaos.set_config(config)
    return {"message": f"Chaos enabled: {config.mode.value}"}


@app.post("/chaos/disable", tags=["chaos"])
async def disable_chaos() -> dict:
    """Kill switch — back to normal."""
    chaos.disable()
    return {"message": "Chaos disabled"}


@app.get("/chaos/status", tags=["chaos"])
async def chaos_status() -> dict:
    cfg = chaos.get_config()
    return {
        "enabled": cfg.mode != ChaosMode.OFF,
        "mode": cfg.mode.value if cfg.mode != ChaosMode.OFF else None,
        "error_rate": cfg.error_rate,
        "latency_min": cfg.latency_min,
        "latency_max": cfg.latency_max,
    }


# ── Business endpoints (what the agent monitors) ─────────────────────


@app.get("/health", response_model=HealthResponse, tags=["api"])
async def health_check():
    start = time.perf_counter()

    await chaos.maybe_inject_latency()

    is_error = chaos.should_return_error()
    degraded = chaos.is_degraded()
    elapsed_ms = (time.perf_counter() - start) * 1000
    _record_event("/health", 500 if is_error else 200, elapsed_ms)

    anomalies.track_request(
        endpoint="/health",
        latency_ms=elapsed_ms,
        is_error=is_error,
        is_degraded=degraded,
    )
    error_rate = anomalies.rolling_error_rate()

    anomalies.record(
        endpoint="/health",
        latency_ms=elapsed_ms,
        error_rate=error_rate,
        is_degraded=degraded,
        status_code=500 if is_error else 200,
    )

    if is_error:
        raise HTTPException(status_code=500, detail="Injected server error")

    return HealthResponse(
        status="degraded" if degraded else "ok",
        endpoint="/health",
        latency_ms=round(elapsed_ms, 2),
        error_rate=round(error_rate, 4),
    )


@app.get("/checkout", response_model=CheckoutResponse, tags=["api"])
async def checkout():
    start = time.perf_counter()

    await chaos.maybe_inject_latency()

    is_error = chaos.should_return_error()
    degraded = chaos.is_degraded()
    elapsed_ms = (time.perf_counter() - start) * 1000
    _record_event("/checkout", 500 if is_error else 200, elapsed_ms)

    anomalies.track_request(
        endpoint="/checkout",
        latency_ms=elapsed_ms,
        is_error=is_error,
        is_degraded=degraded,
    )
    error_rate = anomalies.rolling_error_rate()

    anomalies.record(
        endpoint="/checkout",
        latency_ms=elapsed_ms,
        error_rate=error_rate,
        is_degraded=degraded,
        status_code=500 if is_error else 200,
    )

    if is_error:
        raise HTTPException(status_code=500, detail="Checkout processing failed")

    if degraded:
        return CheckoutResponse(
            order_id=None,
            total=None,
            status="degraded",
            endpoint="/checkout",
            latency_ms=round(elapsed_ms, 2),
            error_rate=round(error_rate, 4),
        )

    return CheckoutResponse(
        order_id=str(uuid.uuid4())[:8],
        total=round(49.99 + (elapsed_ms / 100), 2),
        status="confirmed",
        endpoint="/checkout",
        latency_ms=round(elapsed_ms, 2),
        error_rate=round(error_rate, 4),
    )


# ── Anomaly feed ─────────────────────────────────────────────────────


@app.get("/anomalies", tags=["api"])
async def get_anomalies():
    """Returns recorded anomalies, newest first."""
    return [a.model_dump() for a in anomalies.get_all()]


# ── Stats & metrics (consumed by Incident-Insight-Hub) ───────────────


@app.get("/stats", tags=["api"])
async def get_stats():
    """Computed overview stats from the anomaly and sample stores."""
    return anomalies.get_stats()


@app.get("/metrics/history", tags=["api"])
async def get_metrics_history():
    """Per-minute aggregated health metrics for the last 30 minutes."""
    return anomalies.get_metrics_history()


# ── On-demand analysis ───────────────────────────────────────────────


class AnalyzeRequest(BaseModel):
    endpoint: str
    method: str = "GET"


@app.post("/analyze", tags=["api"])
async def analyze_endpoint(payload: AnalyzeRequest):
    """Hit a local endpoint, record the result, return analysis summary."""
    url = (
        payload.endpoint
        if payload.endpoint.startswith("http")
        else f"{_SELF_BASE}{payload.endpoint}"
    )

    start = time.perf_counter()
    status_code = 0
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.request(payload.method, url, timeout=30.0)
        status_code = resp.status_code
    except httpx.RequestError:
        status_code = 0

    elapsed_ms = (time.perf_counter() - start) * 1000
    is_error = status_code >= 400 or status_code == 0

    anomalies.track_request(
        endpoint=payload.endpoint,
        latency_ms=elapsed_ms,
        is_error=is_error,
    )
    error_rate = anomalies.rolling_error_rate()

    anomaly = anomalies.record(
        endpoint=payload.endpoint,
        latency_ms=elapsed_ms,
        error_rate=error_rate,
        is_degraded=False,
        status_code=status_code,
    )

    return {
        "endpoint": payload.endpoint,
        "method": payload.method,
        "status_code": status_code,
        "latency_ms": round(elapsed_ms, 2),
        "anomaly_detected": anomaly is not None,
    }


# ── Agent pipeline status ─────────────────────────────────────────────


@app.get("/agents/status", tags=["api"])
async def get_agent_status():
    """Returns the state of each agent in the pipeline plus recent traces."""
    return anomalies.get_agent_status()


# ── Legacy metrics endpoint ──────────────────────────────────────────


@app.get("/metrics", tags=["api"])
async def metrics():
    """Returns current chaos state + a timestamp.
    The agent can poll this for a quick status check."""
    cfg = chaos.get_config()
    return {
        "chaos_active": cfg.mode != ChaosMode.OFF,
        "chaos_mode": cfg.mode.value,
        "error_rate": anomalies.rolling_error_rate(),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "buffered_events": len(_recent_events),
    }


# ── Helpers ───────────────────────────────────────────────────────────


def _record_event(endpoint: str, status_code: int, latency_ms: float):
    """Append an observation to the rolling buffer used by /data."""
    _recent_events.append({
        "endpoint": endpoint,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latency_ms": round(latency_ms, 2),
        "status_code": status_code,
        "is_degraded": chaos.is_degraded() and status_code < 400,
        "chaos_mode": chaos.get_config().mode.value,
    })
