"""In-memory anomaly store, request tracker, and metrics aggregator.

The mock API endpoints record every request here. Anomalies are persisted
when chaos injection causes degraded behaviour. The Incident-Insight-Hub
frontend reads from the ``/anomalies``, ``/stats``, and ``/metrics/history``
routes that delegate to this module.
"""

from collections import deque
from dataclasses import dataclass
from datetime import datetime
from time import time as _now
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

BASELINE_LATENCY_MS = 50.0
LATENCY_STD_DEV = 20.0
MAX_STORED_ANOMALIES = 200
MAX_STORED_SAMPLES = 3000
_WINDOW_SECONDS = 60.0
_HISTORY_WINDOW_SECONDS = 1800.0  # 30 minutes


# ── Schema ───────────────────────────────────────────────────────────


class AnomalyRecord(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:8])
    endpoint: str
    z_score: float
    latency_ms: float
    error_rate: float
    is_degraded: bool
    diagnosis: str
    recommended_action: Literal["REROUTE", "ALERT", "WAIT"]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ── Per-request sample (richer than just error flag) ─────────────────


@dataclass(slots=True)
class _Sample:
    timestamp: float
    endpoint: str
    latency_ms: float
    is_error: bool
    is_degraded: bool


# ── Stores ───────────────────────────────────────────────────────────

_store: deque[AnomalyRecord] = deque(maxlen=MAX_STORED_ANOMALIES)
_samples: deque[_Sample] = deque(maxlen=MAX_STORED_SAMPLES)


# ── Anomaly recording ───────────────────────────────────────────────


def record(
    *,
    endpoint: str,
    latency_ms: float,
    error_rate: float,
    is_degraded: bool,
    status_code: int,
) -> AnomalyRecord | None:
    """Evaluate whether the request was anomalous and persist if so."""
    z_score = (latency_ms - BASELINE_LATENCY_MS) / max(LATENCY_STD_DEV, 1.0)

    is_anomalous = (
        z_score > 2.0
        or error_rate > 0.1
        or is_degraded
        or status_code >= 500
    )
    if not is_anomalous:
        return None

    diagnosis = _build_diagnosis(
        z_score=z_score,
        latency_ms=latency_ms,
        error_rate=error_rate,
        is_degraded=is_degraded,
        status_code=status_code,
    )
    action = _pick_action(z_score, error_rate, is_degraded, status_code)

    entry = AnomalyRecord(
        endpoint=endpoint,
        z_score=round(z_score, 2),
        latency_ms=round(latency_ms, 2),
        error_rate=round(error_rate, 4),
        is_degraded=is_degraded,
        diagnosis=diagnosis,
        recommended_action=action,
    )
    _store.appendleft(entry)
    return entry


def get_all() -> list[AnomalyRecord]:
    return list(_store)


def clear() -> None:
    _store.clear()
    _samples.clear()


# ── Request tracking ────────────────────────────────────────────────


def track_request(
    *,
    endpoint: str,
    latency_ms: float,
    is_error: bool,
    is_degraded: bool = False,
) -> None:
    _samples.append(
        _Sample(
            timestamp=_now(),
            endpoint=endpoint,
            latency_ms=latency_ms,
            is_error=is_error,
            is_degraded=is_degraded,
        )
    )


def rolling_error_rate() -> float:
    cutoff = _now() - _WINDOW_SECONDS
    recent = [s for s in _samples if s.timestamp > cutoff]
    if not recent:
        return 0.0
    return sum(1 for s in recent if s.is_error) / len(recent)


# ── Aggregate stats (for /stats) ────────────────────────────────────


def get_stats() -> dict:
    all_anomalies = get_all()
    now = _now()
    active = [
        a
        for a in all_anomalies
        if (now - a.timestamp.timestamp()) < _WINDOW_SECONDS
    ]
    unique_endpoints = {s.endpoint for s in _samples} if _samples else set()

    return {
        "totalIncidents": len(all_anomalies),
        "activeIncidents": len(active),
        "resolvedToday": max(0, len(all_anomalies) - len(active)),
        "mttr": _compute_mttr(),
        "avgConfidence": 0,
        "apisMonitored": len(unique_endpoints) if unique_endpoints else 0,
    }


# ── Metrics history (for /metrics/history) ──────────────────────────


def get_metrics_history() -> list[dict]:
    """Aggregate per-request samples into per-minute buckets."""
    if not _samples:
        return []

    now = _now()
    buckets: dict[str, list[_Sample]] = {}

    for s in _samples:
        if (now - s.timestamp) > _HISTORY_WINDOW_SECONDS:
            continue
        minute_key = datetime.fromtimestamp(s.timestamp).strftime("%H:%M")
        buckets.setdefault(minute_key, []).append(s)

    result: list[dict] = []
    for key in sorted(buckets.keys()):
        samples = buckets[key]
        n = len(samples)
        avg_latency = sum(s.latency_ms for s in samples) / n
        errors = sum(1 for s in samples if s.is_error)
        error_rate_pct = (errors / n) * 100
        uptime_pct = ((n - errors) / n) * 100

        result.append({
            "time": key,
            "latency": round(avg_latency),
            "errorRate": round(error_rate_pct, 1),
            "throughput": n,
            "uptime": round(uptime_pct, 2),
        })

    return result


# ── Private helpers ──────────────────────────────────────────────────


def _compute_mttr() -> str:
    all_anomalies = get_all()
    if len(all_anomalies) < 2:
        return "N/A"
    timestamps = sorted(a.timestamp.timestamp() for a in all_anomalies)
    gaps = [b - a for a, b in zip(timestamps, timestamps[1:])]
    avg_gap_min = (sum(gaps) / len(gaps)) / 60.0
    return f"{avg_gap_min:.1f} min"


def get_agent_status() -> dict:
    """Compute agent pipeline status from anomaly and sample stores."""
    all_anomalies = get_all()
    sample_list = list(_samples)
    now = _now()

    events_processed = len(sample_list)
    anomalies_detected = len(all_anomalies)

    last_anomaly_ts = (
        all_anomalies[0].timestamp.isoformat() if all_anomalies else None
    )
    last_sample_ts = (
        datetime.fromtimestamp(sample_list[-1].timestamp).isoformat()
        if sample_list
        else None
    )

    has_recent = (
        any((now - s.timestamp) < 30.0 for s in sample_list)
        if sample_list
        else False
    )
    monitor_status = "active" if has_recent else "idle"
    diag_status = monitor_status if anomalies_detected > 0 else "idle"

    action_counts = {"REROUTE": 0, "ALERT": 0, "WAIT": 0}
    for a in all_anomalies:
        action_counts[a.recommended_action] += 1

    traces = []
    for a in all_anomalies[:15]:
        traces.append({
            "id": a.id,
            "endpoint": a.endpoint,
            "timestamp": a.timestamp.isoformat(),
            "steps": [
                {
                    "agent": "Monitor Agent",
                    "action": f"Anomaly detected on {a.endpoint}",
                    "result": f"Z-score {a.z_score}, error rate {a.error_rate * 100:.1f}%",
                    "status": "completed",
                },
                {
                    "agent": "Diagnostic Agent",
                    "action": "Root cause analysis",
                    "result": a.diagnosis,
                    "status": "completed",
                },
                {
                    "agent": "Remediation Agent",
                    "action": f"Execute: {a.recommended_action}",
                    "result": _ACTION_LABELS.get(a.recommended_action, "Unknown"),
                    "status": "completed",
                },
            ],
        })

    return {
        "agents": [
            {
                "name": "Monitor Agent",
                "status": monitor_status,
                "description": "Z-score anomaly detection over 60s rolling window",
                "eventsProcessed": events_processed,
                "anomaliesDetected": anomalies_detected,
                "lastActivity": last_sample_ts,
            },
            {
                "name": "Diagnostic Agent",
                "status": diag_status,
                "description": "Pattern-based root cause analysis with LLM fallback",
                "diagnosesGenerated": anomalies_detected,
                "lastActivity": last_anomaly_ts,
            },
            {
                "name": "Remediation Agent",
                "status": diag_status,
                "description": "Automated response — REROUTE, ALERT, or WAIT",
                "actionsExecuted": anomalies_detected,
                "actionBreakdown": action_counts,
                "lastActivity": last_anomaly_ts,
            },
        ],
        "pipeline": {
            "totalRuns": anomalies_detected,
            "thresholdK": 2.5,
            "casesStored": anomalies_detected,
        },
        "recentTraces": traces,
    }


_ACTION_LABELS: dict[str, str] = {
    "REROUTE": "Traffic redirected to backup endpoint",
    "ALERT": "On-call team notified",
    "WAIT": "Transient issue — monitoring, no action taken",
}


# ── Private helpers ──────────────────────────────────────────────────


def _build_diagnosis(
    *,
    z_score: float,
    latency_ms: float,
    error_rate: float,
    is_degraded: bool,
    status_code: int,
) -> str:
    parts: list[str] = []
    if z_score > 2.0:
        parts.append(
            f"Latency spike detected ({latency_ms:.0f}ms, z-score {z_score:.1f})"
        )
    if error_rate > 0.1:
        parts.append(f"Elevated error rate ({error_rate * 100:.1f}%)")
    if is_degraded:
        parts.append("Response degradation — required fields missing")
    if status_code >= 500:
        parts.append(f"Server error (HTTP {status_code})")
    return ". ".join(parts) + "." if parts else "Unknown anomaly."


def _pick_action(
    z_score: float,
    error_rate: float,
    is_degraded: bool,
    status_code: int,
) -> Literal["REROUTE", "ALERT", "WAIT"]:
    if z_score > 5.0 or error_rate > 0.5 or status_code >= 500:
        return "REROUTE"
    if z_score > 3.0 or error_rate > 0.2 or is_degraded:
        return "ALERT"
    return "WAIT"
