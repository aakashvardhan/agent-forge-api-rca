import json
import os
from dotenv import load_dotenv
from gradient import Gradient

load_dotenv()

_client = Gradient(
    access_token=os.getenv("DIGITALOCEAN_ACCESS_TOKEN", ""),
    inference_key=os.getenv("GRADIENT_MODEL_ACCESS_KEY", ""),
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


def diagnose(symptoms: dict, case_context: list = []) -> dict:
    user_content = f"Symptoms: {json.dumps(symptoms)}"

    if case_context:
        cases_str = json.dumps(case_context, indent=2)
        user_content += f"\n\nSimilar past incidents for context:\n{cases_str}"

    response = _client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    )

    raw = response.choices[0].message.content.strip()
    return json.loads(raw)
