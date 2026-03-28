"""Chaos injection engine.

Holds global state for the current chaos mode. The FastAPI middleware
in main.py checks this before every response. Toggle via API endpoints.
"""

import asyncio
import random
from server.schemas import ChaosConfig, ChaosMode


# --- Global mutable state (fine for a single-process hackathon server) ---
_current_config = ChaosConfig(mode=ChaosMode.OFF)


def get_config() -> ChaosConfig:
    return _current_config


def set_config(config: ChaosConfig) -> ChaosConfig:
    global _current_config
    _current_config = config
    return _current_config


def disable() -> ChaosConfig:
    return set_config(ChaosConfig(mode=ChaosMode.OFF))


async def maybe_inject_latency() -> float:
    """If latency mode is active, sleep and return injected delay in ms. Else 0."""
    cfg = _current_config
    if cfg.mode != ChaosMode.LATENCY:
        return 0.0
    delay_ms = random.uniform(cfg.latency_min, cfg.latency_max)
    await asyncio.sleep(delay_ms / 1000.0)
    return delay_ms


def should_return_error() -> bool:
    """If errors mode is active, roll the dice against error_rate."""
    cfg = _current_config
    if cfg.mode != ChaosMode.ERRORS:
        return False
    return random.random() < cfg.error_rate


def is_degraded() -> bool:
    """If degraded mode is active, endpoints return partial data."""
    return _current_config.mode == ChaosMode.DEGRADED