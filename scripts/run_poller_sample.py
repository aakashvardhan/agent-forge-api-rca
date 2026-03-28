"""Run the poller across all chaos modes and save events to a JSON file.

Cycles through: baseline → errors → degraded → latency → back to off,
capturing events from each phase so the output shows all event flavors.

Usage:
    python -m scripts.run_poller_sample
"""

import asyncio
import json
from pathlib import Path

import httpx

from ingestion.poller import Poller
from server.schemas import NormalizedEvent

OUTPUT_PATH = Path("data/poller_events.json")
BASE_URL = "http://localhost:8000"
POLL_INTERVAL = 0.5

CHAOS_PHASES = [
    ("baseline (chaos off)", None),
    ("error bursts (50%)", {"mode": "errors", "error_rate": 0.5}),
    ("degraded responses", {"mode": "degraded"}),
    ("latency spikes", {"mode": "latency", "latency_min": 1.0, "latency_max": 2.0}),
]
CYCLES_PER_PHASE = 3


async def set_chaos(client: httpx.AsyncClient, config: dict | None):
    if config is None:
        await client.post(f"{BASE_URL}/chaos/disable")
    else:
        await client.post(f"{BASE_URL}/chaos/enable", json=config)


async def main():
    collected: list[dict] = []

    async def collect_event(event: NormalizedEvent):
        record = event.model_dump(mode="json")
        record["_phase"] = current_phase
        collected.append(record)
        flag = ""
        if event.is_degraded:
            flag = " ⚠ DEGRADED"
        elif event.status_code >= 400 or event.status_code == 0:
            flag = " ✗ ERROR"
        print(f"  [{event.endpoint}] status={event.status_code}  "
              f"latency={event.latency_ms:.1f}ms  "
              f"error_rate={event.error_rate_1m:.0%}{flag}")

    poller = Poller(
        base_url=BASE_URL,
        on_event=collect_event,
        interval=POLL_INTERVAL,
    )

    current_phase = ""

    async with httpx.AsyncClient(timeout=10.0) as api_client:
        poller._running = True
        http_client = httpx.AsyncClient(timeout=10.0)

        for phase_name, chaos_config in CHAOS_PHASES:
            current_phase = phase_name
            print(f"\n── Phase: {phase_name} ──")
            await set_chaos(api_client, chaos_config)
            await asyncio.sleep(0.3)

            async with httpx.AsyncClient(timeout=10.0) as poll_client:
                for _ in range(CYCLES_PER_PHASE):
                    tasks = [
                        poller._poll_endpoint(poll_client, ep)
                        for ep in poller._endpoints
                    ]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await asyncio.sleep(POLL_INTERVAL)

        print(f"\n── Restoring baseline ──")
        await set_chaos(api_client, None)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(collected, indent=2, default=str))
    print(f"\n{len(collected)} events saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
