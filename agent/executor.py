from enum import Enum


class Action(str, Enum):
    REROUTE = "REROUTE"
    ALERT   = "ALERT"
    WAIT    = "WAIT"


def execute(result: dict) -> None:
    action = result.get("action")
    diagnosis = result.get("diagnosis", "")

    if action == Action.REROUTE:
        _reroute(diagnosis)
    elif action == Action.ALERT:
        _alert(diagnosis)
    else:
        _wait(diagnosis)


def _reroute(diagnosis: str) -> None:
    print(f"[REROUTE] Redirecting traffic to backup endpoint. Reason: {diagnosis}")


def _alert(diagnosis: str) -> None:
    print(f"[ALERT] Notifying on-call team. Reason: {diagnosis}")


def _wait(diagnosis: str) -> None:
    print(f"[WAIT] Transient issue — monitoring, no action taken. Reason: {diagnosis}")
