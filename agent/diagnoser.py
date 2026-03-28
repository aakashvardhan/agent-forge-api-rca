import json
import logging
import os
from dotenv import load_dotenv
from gradient import Gradient

logger = logging.getLogger(__name__)

load_dotenv()

_client = Gradient(
    access_token=os.getenv("DIGITALOCEAN_ACCESS_TOKEN", ""),
    model_access_key=os.getenv("GRADIENT_MODEL_ACCESS_KEY", ""),
)
MODEL_NAME = os.getenv("GRADIENT_MODEL", "llama3.3-70b-instruct")

SYSTEM_PROMPT = """You are an API reliability expert. Given symptoms from a monitored API endpoint,
diagnose the root cause and recommend one action.

Respond ONLY with valid JSON in this exact format:
{"diagnosis": "<root cause explanation>", "action": "<REROUTE|ALERT|WAIT>"}

Action definitions:
- REROUTE: redirect traffic to a backup endpoint
- ALERT: notify the on-call team, no automated fix
- WAIT: transient issue, monitor and do nothing yet"""


_DEFAULT_RESULT = {"diagnosis": "Unable to parse LLM response", "action": "WAIT"}
_MAX_RETRIES = 2


def diagnose(symptoms: dict, case_context: list = []) -> dict:
    user_content = f"Symptoms: {json.dumps(symptoms)}"

    if case_context:
        cases_str = json.dumps(case_context, indent=2)
        user_content += f"\n\nSimilar past incidents for context:\n{cases_str}"

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    for attempt in range(_MAX_RETRIES):
        response = _client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
        )
        raw = response.choices[0].message.content.strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "Attempt %d/%d: LLM returned non-JSON response: %s",
                attempt + 1, _MAX_RETRIES, raw[:200],
            )

    logger.error("All %d attempts returned non-JSON; defaulting to WAIT", _MAX_RETRIES)
    return _DEFAULT_RESULT
