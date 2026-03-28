import math
from collections import defaultdict, deque
from datetime import timedelta

import agent.state as _state
from server.schemas import NormalizedEvent

WINDOW_SECONDS = 60

_windows: dict[str, deque] = defaultdict(deque)


def _prune(window: deque, now) -> None:
    cutoff = now - timedelta(seconds=WINDOW_SECONDS)
    while window and window[0][0] < cutoff:
        window.popleft()


def _z_score(value: float, window: deque) -> float:
    if len(window) < 2:
        return 0.0
    values = [v for _, v in window]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    stddev = math.sqrt(variance)
    if stddev == 0:
        return 0.0
    return (value - mean) / stddev


def check(event: NormalizedEvent) -> dict | None:
    """Returns a symptoms dict if the event is anomalous, None if normal.

    The returned dict is passed directly to diagnoser.diagnose() as symptoms.
    Anomaly triggers: latency z-score > THRESHOLD_K, error_rate > 10%, or is_degraded.
    """
    window = _windows[event.endpoint]
    _prune(window, event.timestamp)

    z = _z_score(event.latency_ms, window)
    window.append((event.timestamp, event.latency_ms))

    anomalous = (
        z > _state.THRESHOLD_K
        or event.error_rate_1m > 0.1
        or event.is_degraded
    )

    if not anomalous:
        return None

    return {
        "endpoint": event.endpoint,
        "z_score": round(z, 3),
        "latency_ms": event.latency_ms,
        "error_rate_1m": event.error_rate_1m,
        "is_degraded": event.is_degraded,
        "status_code": event.status_code,
        "error_detail": event.error_detail,
    }
