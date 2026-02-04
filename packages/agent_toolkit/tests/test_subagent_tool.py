from __future__ import annotations

from agent_toolkit.subagents.models import SubagentResult
from agent_toolkit.tools.subagents import subagent


def test_subagent_tool_rejects_invalid_mode() -> None:
    response = subagent(tasks=[], mode="invalid")
    assert "Invalid subagent mode" in response


def test_subagent_tool_requires_tasks() -> None:
    response = subagent(tasks=[], mode="chain")
    assert response == "No valid subagent tasks provided."


def test_subagent_tool_formats_results(monkeypatch) -> None:
    class FakeRunner:
        def run_tasks(self, _tasks, mode="chain"):
            return [SubagentResult(agent="scout", prompt="", output="ok")]

    monkeypatch.setattr("agent_toolkit.tools.subagents.SubagentRunner", lambda: FakeRunner())

    response = subagent(tasks=[{"agent": "scout", "prompt": "Hi"}], mode="chain")
    assert "Subagent results" in response
    assert "scout" in response
    assert "ok" in response
