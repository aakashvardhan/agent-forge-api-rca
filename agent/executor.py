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
    pass  # TODO: redirect traffic to backup endpoint


def _alert(diagnosis: str) -> None:
    pass  # TODO: notify on-call team


def _wait(diagnosis: str) -> None:
    pass  # TODO: log that issue is being monitored
