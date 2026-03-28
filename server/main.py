"""AgentForge mock API server.

Two business endpoints (/health, /checkout) that behave normally
until you flip the chaos toggle. The agent monitors these.

Run: uvicorn server.main:app --port 8000
"""

import time
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException
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

    # Chaos: latency injection
    injected_ms = await chaos.maybe_inject_latency()

    # Chaos: error burst
    if chaos.should_return_error():
        raise HTTPException(status_code=500, detail="Injected server error")

    elapsed_ms = (time.perf_counter() - start) * 1000

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
        raise HTTPException(status_code=500, detail="Checkout processing failed")

    elapsed_ms = (time.perf_counter() - start) * 1000

    # Degraded mode: return partial response (missing order_id and total)
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
        "timestamp": datetime.utcnow().isoformat(),
    }