"""Integration tests for agent.loop — end-to-end pipeline from event to action.

These tests verify the full detect → diagnose → execute → store → tune flow
with the LLM client mocked out.
"""

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import agent.state as _state
from agent.detector import _windows
from agent.loop import on_event
from memory.auto_tune import _history
from memory.case_store import _cases
from server.schemas import NormalizedEvent


def _make_event(
    endpoint="/health",
    latency_ms=50.0,
    status_code=500,
    error_rate_1m=0.8,
    is_degraded=False,
    error_detail="Injected server error",
) -> NormalizedEvent:
    return NormalizedEvent(
        endpoint=endpoint,
        timestamp=datetime.now(timezone.utc),
        latency_ms=latency_ms,
        status_code=status_code,
        error_rate_1m=error_rate_1m,
        is_degraded=is_degraded,
        error_detail=error_detail,
        source="poller",
    )


def _mock_llm_response(content: str):
    choice = SimpleNamespace(message=SimpleNamespace(content=content))
    return SimpleNamespace(choices=[choice])


@pytest.fixture(autouse=True)
def _reset_all():
    _windows.clear()
    _cases.clear()
    _history.clear()
    original_k = _state.THRESHOLD_K
    _state.THRESHOLD_K = 2.5
    yield
    _windows.clear()
    _cases.clear()
    _history.clear()
    _state.THRESHOLD_K = original_k


class TestOnEventNormalTraffic:
    @pytest.mark.asyncio
    async def test_normal_event_triggers_nothing(self):
        event = _make_event(
            status_code=200,
            error_rate_1m=0.0,
            error_detail=None,
        )

        with patch("agent.diagnoser._client") as mock_client:
            await on_event(event)
            mock_client.chat.completions.create.assert_not_called()

        assert len(_cases) == 0


class TestOnEventAnomalousFlow:
    @pytest.mark.asyncio
    async def test_high_error_rate_triggers_full_pipeline(self):
        event = _make_event(error_rate_1m=0.8, status_code=500)
        llm_result = {"diagnosis": "Server overloaded", "action": "REROUTE"}

        with patch("agent.diagnoser._client") as mock_client:
            mock_client.chat.completions.create.return_value = _mock_llm_response(
                json.dumps(llm_result)
            )
            await on_event(event)

        assert len(_cases) == 1
        assert _cases[0]["action"] == "REROUTE"
        assert _cases[0]["diagnosis"] == "Server overloaded"

    @pytest.mark.asyncio
    async def test_degraded_event_triggers_pipeline(self):
        event = _make_event(
            status_code=200,
            error_rate_1m=0.0,
            is_degraded=True,
            error_detail=None,
        )
        llm_result = {"diagnosis": "Partial outage", "action": "ALERT"}

        with patch("agent.diagnoser._client") as mock_client:
            mock_client.chat.completions.create.return_value = _mock_llm_response(
                json.dumps(llm_result)
            )
            await on_event(event)

        assert len(_cases) == 1
        assert _cases[0]["action"] == "ALERT"

    @pytest.mark.asyncio
    async def test_auto_tune_updates_after_action(self):
        event = _make_event(error_rate_1m=0.9)
        llm_result = {"diagnosis": "overload", "action": "WAIT"}

        with patch("agent.diagnoser._client") as mock_client:
            mock_client.chat.completions.create.return_value = _mock_llm_response(
                json.dumps(llm_result)
            )
            await on_event(event)
            await on_event(event)

        assert len(_history) == 2
        assert list(_history) == ["WAIT", "WAIT"]


class TestOnEventCaseContextUsed:
    @pytest.mark.asyncio
    async def test_second_anomaly_gets_case_context(self):
        first = _make_event(error_rate_1m=0.8)
        second = _make_event(error_rate_1m=0.9)

        with patch("agent.diagnoser._client") as mock_client:
            mock_client.chat.completions.create.return_value = _mock_llm_response(
                '{"diagnosis": "recurring issue", "action": "REROUTE"}'
            )
            await on_event(first)
            await on_event(second)

        assert len(_cases) == 2
        # Verify the second call included case context by checking call args
        calls = mock_client.chat.completions.create.call_args_list
        second_call_messages = (
            calls[1].kwargs.get("messages") or calls[1][1].get("messages")
        )
        user_msg = next(m for m in second_call_messages if m["role"] == "user")
        assert "Similar past incidents" in user_msg["content"]


class TestOnEventMultipleEndpoints:
    @pytest.mark.asyncio
    async def test_different_endpoints_stored_separately(self):
        health_event = _make_event(endpoint="/health", error_rate_1m=0.8)
        checkout_event = _make_event(endpoint="/checkout", error_rate_1m=0.7)

        with patch("agent.diagnoser._client") as mock_client:
            mock_client.chat.completions.create.return_value = _mock_llm_response(
                '{"diagnosis": "test", "action": "ALERT"}'
            )
            await on_event(health_event)
            await on_event(checkout_event)

        endpoints = {c["endpoint"] for c in _cases}
        assert endpoints == {"/health", "/checkout"}
