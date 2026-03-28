from datetime import datetime, timezone
import agent.state as _state

_cases: list[dict] = []


def save(symptoms: dict, result: dict) -> None:
    _cases.append({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoint": symptoms["endpoint"],
        "symptoms": symptoms,
        "diagnosis": result["diagnosis"],
        "action": result["action"],
    })


def get_similar(symptoms: dict, k: int = 3) -> list:
    endpoint = symptoms["endpoint"]
    scored = []

    for case in _cases:
        if case["endpoint"] != endpoint:
            continue

        score = 0
        past = case["symptoms"]
        if past.get("z_score", 0) > _state.THRESHOLD_K:
            score += 1
        if past.get("error_rate_1m", 0) > 0.1:
            score += 1
        if past.get("is_degraded"):
            score += 1

        if score > 0:
            scored.append((score, case))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [case for _, case in scored[:k]]
