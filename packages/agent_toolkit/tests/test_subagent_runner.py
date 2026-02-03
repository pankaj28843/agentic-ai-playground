from __future__ import annotations

from agent_toolkit.models.profiles import AgentProfile
from agent_toolkit.subagents.models import SubagentDefinition, SubagentTask
from agent_toolkit.subagents.runner import SubagentRunner


class DummyAgent:
    def __init__(self, label: str) -> None:
        self._label = label

    def __call__(self, prompt: str) -> str:
        return f"{self._label}:{prompt}"


class DummyFactory:
    def create_from_profile(self, profile, **_kwargs):
        return DummyAgent(profile.name)


def test_subagent_runner_chain(monkeypatch) -> None:
    profiles = {
        "planner": AgentProfile(
            name="planner",
            description="planner",
            model="",
            system_prompt="",
            tools=[],
            tool_groups=[],
            extends="",
            metadata={},
            constraints={},
        )
    }
    definitions = {
        "scout": SubagentDefinition(
            name="scout",
            description="scout",
            system_prompt="scout",
            model="",
            tools=[],
            tool_groups=[],
            source="global",
        )
    }

    monkeypatch.setattr(
        "agent_toolkit.subagents.runner.get_mcp_clients_for_profile", lambda _profile: []
    )

    runner = SubagentRunner(
        profiles=profiles,
        definitions=definitions,
        tool_groups={},
        factory=DummyFactory(),
    )

    results = runner.run_tasks(
        [
            SubagentTask(agent="planner", prompt="Plan the work"),
            SubagentTask(agent="planner", prompt="Refine the plan"),
        ],
        mode="chain",
    )

    assert len(results) == 2
    assert results[0].output.startswith("planner:Plan the work")
    assert "Context from previous agent" in results[1].output


def test_subagent_runner_parallel(monkeypatch) -> None:
    profiles = {
        "planner": AgentProfile(
            name="planner",
            description="planner",
            model="",
            system_prompt="",
            tools=[],
            tool_groups=[],
            extends="",
            metadata={},
            constraints={},
        )
    }

    monkeypatch.setattr(
        "agent_toolkit.subagents.runner.get_mcp_clients_for_profile", lambda _profile: []
    )

    runner = SubagentRunner(
        profiles=profiles,
        definitions={},
        tool_groups={},
        factory=DummyFactory(),
    )

    results = runner.run_tasks(
        [
            SubagentTask(agent="planner", prompt="Task A"),
            SubagentTask(agent="planner", prompt="Task B"),
        ],
        mode="parallel",
    )

    outputs = {result.output for result in results}
    assert outputs == {"planner:Task A", "planner:Task B"}


def test_subagent_runner_unknown_agent(monkeypatch) -> None:
    monkeypatch.setattr(
        "agent_toolkit.subagents.runner.get_mcp_clients_for_profile", lambda _profile: []
    )

    runner = SubagentRunner(
        profiles={},
        definitions={},
        tool_groups={},
        factory=DummyFactory(),
    )

    results = runner.run_tasks([SubagentTask(agent="missing", prompt="Task")], mode="chain")
    assert results[0].error == "Unknown subagent: missing"
