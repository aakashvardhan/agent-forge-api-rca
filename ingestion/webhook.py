"""Webhook receiver for Nexla-pushed events.

Nexla calls POST /ingest with a JSON body matching NormalizedEvent.
This module runs a tiny FastAPI app on a separate port (8001) that
forwards events to the agent's ingest callback.

Key behaviors:
  - Returns 503 if no callback is registered (agent not ready)
  - Logs every received event at DEBUG, errors at ERROR
  - Catches callback exceptions and returns 500 without crashing
  - Tracks event count via GET /stats for observability

Usage:
    receiver = WebhookReceiver(on_event=my_agent.ingest)
    await receiver.start(port=8001)
"""

import logging
from typing import Callable, Awaitable

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from server.schemas import NormalizedEvent

logger = logging.getLogger(__name__)


class WebhookReceiver:
    def __init__(
        self,
        on_event: Callable[[NormalizedEvent], Awaitable[None]] | None = None,
    ):
        self._callback = on_event
        self._event_count = 0
        self._error_count = 0
        self._app = self._build_app()

    def _build_app(self) -> FastAPI:
        app = FastAPI(title="AgentForge Ingestion Webhook")

        @app.post("/ingest")
        async def ingest(event: NormalizedEvent):
            # No callback = agent not connected yet
            if self._callback is None:
                logger.warning(
                    "Event received but no callback registered — returning 503"
                )
                raise HTTPException(
                    status_code=503,
                    detail="Agent not ready — no callback registered",
                )

            try:
                await self._callback(event)
                self._event_count += 1
                logger.debug(
                    "Event ingested: endpoint=%s status=%d event_id=%s (total: %d)",
                    event.endpoint, event.status_code, event.event_id, self._event_count,
                )
                return {"status": "received", "event_id": event.event_id}

            except Exception as exc:
                self._error_count += 1
                logger.error(
                    "Callback failed for event %s: %s", event.event_id, exc,
                )
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "callback_error",
                        "event_id": event.event_id,
                        "detail": str(exc)[:200],
                    },
                )

        @app.get("/stats")
        async def stats():
            """Quick observability endpoint — check if Nexla is pushing."""
            return {
                "events_received": self._event_count,
                "callback_errors": self._error_count,
                "callback_registered": self._callback is not None,
            }

        @app.get("/health")
        async def health():
            if self._callback is None:
                raise HTTPException(status_code=503, detail="No callback")
            return {"status": "ok"}

        return app

    async def start(self, host: str = "0.0.0.0", port: int = 8001):
        import uvicorn

        logger.info("Webhook receiver starting on %s:%d", host, port)
        config = uvicorn.Config(self._app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()