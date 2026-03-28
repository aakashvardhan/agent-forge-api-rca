"""AgentForge mock API server.

Two business endpoints (/health, /checkout) that behave normally
until you flip the chaos toggle.  The agent monitors these.

Run: uvicorn server.main:app --port 8000
"""

import os
import time
import uuid
from datetime import datetime

import httpx
from fastapi import FastAPI, HTTPException
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

_SELF_BASE = os.getenv("AGENTFORGE_BASE_URL", "http://localhost:8000")


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
    """Returns current chaos state + a timestamp."""
    cfg = chaos.get_config()
    return {
        "chaos_active": cfg.mode != ChaosMode.OFF,
        "chaos_mode": cfg.mode.value,
        "error_rate": anomalies.rolling_error_rate(),
        "timestamp": datetime.utcnow().isoformat(),
    }
