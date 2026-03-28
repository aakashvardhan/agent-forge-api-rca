import logging
from collections import deque

import agent.state as _state

logger = logging.getLogger(__name__)

_MIN_THRESHOLD = 1.5
_MAX_THRESHOLD = 5.0
_MAX_STEP = 0.2
_WINDOW = 10

_history: deque[str] = deque(maxlen=_WINDOW)


def update(action: str) -> None:
    if action not in ("WAIT", "REROUTE", "ALERT"):
        return

    _history.append(action)

    if len(_history) < 2:
        return

    wait_rate = sum(1 for a in _history if a == "WAIT") / len(_history)
    adjustment = (wait_rate - 0.5) * _MAX_STEP

    old = _state.THRESHOLD_K
    _state.THRESHOLD_K = round(
        max(_MIN_THRESHOLD, min(_MAX_THRESHOLD, old + adjustment)), 3
    )

    if _state.THRESHOLD_K != old:
        logger.info(
            "THRESHOLD_K adjusted: %.3f -> %.3f (wait_rate=%.0f%% over last %d actions)",
            old, _state.THRESHOLD_K, wait_rate * 100, len(_history),
        )
