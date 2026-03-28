import asyncio
import logging

from ingestion.poller import Poller
from ingestion.webhook import WebhookReceiver
from agent import detector, diagnoser, executor
from memory import case_store, auto_tune
from server.schemas import NormalizedEvent

logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"


async def on_event(event: NormalizedEvent) -> None:
    symptoms = detector.check(event)
    if symptoms is None:
        return

    logger.info(
        "Anomaly on %s — z=%.2f error_rate=%.2f degraded=%s",
        event.endpoint, symptoms["z_score"], symptoms["error_rate_1m"], symptoms["is_degraded"],
    )

    case_context = case_store.get_similar(symptoms)
    result = diagnoser.diagnose(symptoms, case_context)
    logger.info("Action: %s | %s", result["action"], result["diagnosis"])

    executor.execute(result)
    case_store.save(symptoms, result)
    auto_tune.update(result["action"])


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    logger.info("AgentForge starting")

    poller = Poller(base_url=BASE_URL, on_event=on_event)
    receiver = WebhookReceiver(on_event=on_event)

    await asyncio.gather(
        poller.start(),
        receiver.start(port=8001),
    )


if __name__ == "__main__":
    asyncio.run(main())
