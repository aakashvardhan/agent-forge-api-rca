"""Tests for agent.executor — action dispatch (REROUTE, ALERT, WAIT)."""

from agent.executor import Action, execute


class TestActionEnum:
    def test_enum_values(self):
        assert Action.REROUTE.value == "REROUTE"
        assert Action.ALERT.value == "ALERT"
        assert Action.WAIT.value == "WAIT"

    def test_str_comparison(self):
        assert Action.REROUTE == "REROUTE"
        assert Action.ALERT == "ALERT"
        assert Action.WAIT == "WAIT"


class TestExecuteReroute:
    def test_reroute_prints_message(self, capsys):
        execute({"action": "REROUTE", "diagnosis": "high latency"})
        captured = capsys.readouterr()
        assert "[REROUTE]" in captured.out
        assert "high latency" in captured.out

    def test_reroute_via_enum(self, capsys):
        execute({"action": Action.REROUTE, "diagnosis": "test"})
        assert "[REROUTE]" in capsys.readouterr().out


class TestExecuteAlert:
    def test_alert_prints_message(self, capsys):
        execute({"action": "ALERT", "diagnosis": "error rate spike"})
        captured = capsys.readouterr()
        assert "[ALERT]" in captured.out
        assert "error rate spike" in captured.out


class TestExecuteWait:
    def test_wait_prints_message(self, capsys):
        execute({"action": "WAIT", "diagnosis": "transient blip"})
        captured = capsys.readouterr()
        assert "[WAIT]" in captured.out
        assert "transient blip" in captured.out


class TestExecuteFallback:
    def test_unknown_action_falls_through_to_wait(self, capsys):
        execute({"action": "UNKNOWN", "diagnosis": "fallback test"})
        captured = capsys.readouterr()
        assert "[WAIT]" in captured.out

    def test_missing_action_key_falls_through_to_wait(self, capsys):
        execute({"diagnosis": "no action key"})
        captured = capsys.readouterr()
        assert "[WAIT]" in captured.out

    def test_missing_diagnosis_uses_empty_string(self, capsys):
        execute({"action": "ALERT"})
        captured = capsys.readouterr()
        assert "[ALERT]" in captured.out
