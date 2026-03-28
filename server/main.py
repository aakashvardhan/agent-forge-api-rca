"""AgentForge mock API server.

Two business endpoints (/health, /checkout) that behave normally
until you flip the chaos toggle. The agent monitors these.

Run: uvicorn server.main:app --port 8000
"""

import time
import uuid
from collections import deque
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from server.schemas import (
    ChaosConfig,
    ChaosMode,
    CheckoutResponse,
    HealthResponse,
)
from server import chaos

app = FastAPI(title="AgentForge Mock API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rolling buffer of recent events for the /data endpoint (Nexla-friendly)
MAX_EVENT_BUFFER = 100
_recent_events: deque[dict] = deque(maxlen=MAX_EVENT_BUFFER)


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
    # Always include a live sample from each monitored endpoint
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
    result = chaos.set_config(config)
    return {"status": "chaos_enabled", "config": result.model_dump()}


@app.post("/chaos/disable", tags=["chaos"])
async def disable_chaos() -> dict:
    """Kill switch — back to normal."""
    chaos.disable()
    return {"status": "chaos_disabled"}


@app.get("/chaos/status", tags=["chaos"])
async def chaos_status() -> dict:
    return {"config": chaos.get_config().model_dump()}


# ── Business endpoints (what the agent monitors) ─────────────────────

@app.get("/health", response_model=HealthResponse, tags=["api"])
async def health_check():
    start = time.perf_counter()

    injected_ms = await chaos.maybe_inject_latency()

    if chaos.should_return_error():
        _record_event("/health", 500, (time.perf_counter() - start) * 1000)
        raise HTTPException(status_code=500, detail="Injected server error")

    elapsed_ms = (time.perf_counter() - start) * 1000
    _record_event("/health", 200, elapsed_ms)

    return HealthResponse(
        status="degraded" if chaos.is_degraded() else "ok",
        endpoint="/health",
        latency_ms=round(elapsed_ms, 2),
    )


@app.get("/checkout", response_model=CheckoutResponse, tags=["api"])
async def checkout():
    start = time.perf_counter()

    injected_ms = await chaos.maybe_inject_latency()

    if chaos.should_return_error():
        _record_event("/checkout", 500, (time.perf_counter() - start) * 1000)
        raise HTTPException(status_code=500, detail="Checkout processing failed")

    elapsed_ms = (time.perf_counter() - start) * 1000
    _record_event("/checkout", 200, elapsed_ms)

    if chaos.is_degraded():
        return CheckoutResponse(
            order_id=None,
            total=None,
            status="confirmed",
        )

    return CheckoutResponse(
        order_id=str(uuid.uuid4())[:8],
        total=round(49.99 + (elapsed_ms / 100), 2),
        status="confirmed",
    )


# ── Metrics endpoint (convenience for the agent/dashboard) ───────────

@app.get("/metrics", tags=["api"])
async def metrics():
    """Returns current chaos state + a timestamp.
    The agent can poll this for a quick status check."""
    cfg = chaos.get_config()
    return {
        "chaos_active": cfg.mode != ChaosMode.OFF,
        "chaos_mode": cfg.mode.value,
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