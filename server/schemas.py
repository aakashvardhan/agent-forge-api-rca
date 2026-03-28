"""Shared event schemas for AgentForge.

These models define the contract between the mock API server,
the ingestion layer (Nexla/poller), and the agent's detector.

Schema version: 1
"""

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field, model_validator


# ── Mock server schemas ──────────────────────────────────────────────


class ChaosMode(str, Enum):
    """Types of failure injection the chaos server can produce."""
    LATENCY = "latency"       # asyncio.sleep(2-5s)
    ERRORS = "errors"         # random 500s at configurable rate
    DEGRADED = "degraded"     # 200 but missing fields
    OFF = "off"


class ChaosConfig(BaseModel):
    """Request body for POST /chaos/enable."""
    mode: ChaosMode = ChaosMode.LATENCY
    error_rate: float = Field(0.5, ge=0.0, le=1.0, description="Fraction of requests that fail (errors mode)")
    latency_min: float = Field(2.0, ge=0.0, description="Min injected delay in seconds")
    latency_max: float = Field(5.0, ge=0.0, description="Max injected delay in seconds")


class HealthResponse(BaseModel):
    """Response from /health endpoint."""
    status: str = "ok"
    endpoint: str
    latency_ms: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CheckoutResponse(BaseModel):
    """Response from /checkout endpoint. In degraded mode, optional fields go None."""
    order_id: str | None = None
    total: float | None = None
    status: str = "confirmed"
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Unified event schema (the only thing the agent consumes) ─────────


EventSource = Literal["health_check", "nexla", "poller"]


class NormalizedEvent(BaseModel):
    """The single schema that flows from ingestion → agent.

    Whether Nexla or the fallback poller produces it,
    it must conform to this shape. All downstream components
    (detector, diagnoser, case memory) depend on this contract.

    Key invariants:
      - is_degraded is only True when status_code < 400
      - event_id is unique per event (not a distributed trace ID)
      - error_detail is only populated on 4xx/5xx responses
    """

    # ── Identity ──
    event_id: str = Field(
        default_factory=lambda: uuid4().hex,
        description="Unique event ID for correlating detection → diagnosis → action → outcome",
    )

    # ── Core fields ──
    endpoint: str                       # e.g. "/health", "/checkout"
    timestamp: datetime
    latency_ms: float                   # response time of the upstream call
    status_code: int                    # HTTP status code (0 = connection failure/timeout)

    # ── Computed metrics ──
    error_rate_1m: float = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Rolling 1-min error rate, computed by the ingestion layer",
    )

    # ── Failure context ──
    is_degraded: bool = Field(
        False,
        description=(
            "True when status is 2xx/3xx but the response body is missing "
            "required fields. Set by the poller via response body inspection. "
            "NOTE: Nexla path does not set this — use the X-Degraded response "
            "header as the source of truth when Nexla is the ingestion layer."
        ),
    )
    error_detail: str | None = Field(
        None,
        max_length=500,
        description="Truncated error message from 4xx/5xx responses. None on success.",
    )

    # ── Metadata ──
    source: EventSource = "poller"
    schema_version: int = Field(1, description="Bump when fields change")

    # ── Validators ──

    @model_validator(mode="after")
    def degraded_requires_success_status(self) -> "NormalizedEvent":
        """is_degraded only makes sense on responses that *look* successful."""
        if self.is_degraded and self.status_code >= 400:
            raise ValueError(
                f"is_degraded=True is invalid with status_code={self.status_code}. "
                "Degraded means 2xx/3xx with bad body, not an outright error."
            )
        return self

    @model_validator(mode="after")
    def error_detail_only_on_failure(self) -> "NormalizedEvent":
        """Warn (don't crash) if error_detail is set on a success response."""
        if self.error_detail and self.status_code < 400 and self.status_code != 0:
            self.error_detail = None
        return self