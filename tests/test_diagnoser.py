"""Tests for agent.diagnoser — LLM-powered diagnosis with Gradient API."""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agent import diagnoser


def _mock_llm_response(content: str):
    """Build a mock matching Gradient chat completion structure."""
    choice = SimpleNamespace(message=SimpleNamespace(content=content))
    return SimpleNamespace(choices=[choice])


@pytest.fixture
def sample_symptoms():
    return {
        "endpoint": "/health",
        "z_score": 3.5,
        "latency_ms": 5000.0,
        "error_rate_1m": 0.8,
        "is_degraded": False,
        "status_code": 500,
        "error_detail": "Injected server error",
    }


class TestDiagnoseValidJSON:
    @patch.object(diagnoser, "_client")
    def test_returns_parsed_json(self, mock_client, sample_symptoms):
        expected = {"diagnosis": "Server overloaded", "action": "REROUTE"}
        mock_client.chat.completions.create.return_value = _mock_llm_response(
            json.dumps(expected)
        )

        result = diagnoser.diagnose(sample_symptoms)

        assert result == expected
        mock_client.chat.completions.create.assert_called_once()

    @patch.object(diagnoser, "_client")
    def test_passes_symptoms_in_user_message(self, mock_client, sample_symptoms):
        mock_client.chat.completions.create.return_value = _mock_llm_response(
            '{"diagnosis": "test", "action": "WAIT"}'
        )

        diagnoser.diagnose(sample_symptoms)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        user_msg = next(m for m in messages if m["role"] == "user")
        assert json.dumps(sample_symptoms) in user_msg["content"]


class TestDiagnoseWithCaseContext:
    @patch.object(diagnoser, "_client")
    def test_includes_case_context_in_prompt(self, mock_client, sample_symptoms):
        mock_client.chat.completions.create.return_value = _mock_llm_response(
            '{"diagnosis": "known issue", "action": "ALERT"}'
        )
        past_cases = [{"endpoint": "/health", "action": "REROUTE", "diagnosis": "overload"}]

        diagnoser.diagnose(sample_symptoms, case_context=past_cases)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        user_msg = next(m for m in messages if m["role"] == "user")
        assert "Similar past incidents" in user_msg["content"]
        assert "overload" in user_msg["content"]


class TestDiagnoseRetryOnInvalidJSON:
    @patch.object(diagnoser, "_client")
    def test_retries_on_non_json_then_succeeds(self, mock_client, sample_symptoms):
        valid = '{"diagnosis": "recovered", "action": "WAIT"}'
        mock_client.chat.completions.create.side_effect = [
            _mock_llm_response("This is not JSON"),
            _mock_llm_response(valid),
        ]

        result = diagnoser.diagnose(sample_symptoms)

        assert result["action"] == "WAIT"
        assert mock_client.chat.completions.create.call_count == 2

    @patch.object(diagnoser, "_client")
    def test_all_retries_fail_returns_default(self, mock_client, sample_symptoms):
        mock_client.chat.completions.create.return_value = _mock_llm_response(
            "I cannot produce JSON"
        )

        result = diagnoser.diagnose(sample_symptoms)

        assert result == diagnoser._DEFAULT_RESULT
        assert result["action"] == "WAIT"
        assert mock_client.chat.completions.create.call_count == diagnoser._MAX_RETRIES


class TestDiagnoseSystemPrompt:
    @patch.object(diagnoser, "_client")
    def test_system_prompt_contains_action_definitions(self, mock_client, sample_symptoms):
        mock_client.chat.completions.create.return_value = _mock_llm_response(
            '{"diagnosis": "x", "action": "WAIT"}'
        )

        diagnoser.diagnose(sample_symptoms)

        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs.get("messages") or call_args[1].get("messages")
        system_msg = next(m for m in messages if m["role"] == "system")
        for action in ("REROUTE", "ALERT", "WAIT"):
            assert action in system_msg["content"]
