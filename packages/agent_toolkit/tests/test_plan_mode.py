from __future__ import annotations

from agent_toolkit.agents.factory import AgentFactory
from agent_toolkit.hooks.plan_mode import PlanModeHook
from agent_toolkit.models.profiles import AgentProfile
from agent_toolkit.plan_mode import DEFAULT_SHELL_ALLOWLIST, PlanModeSettings
from agent_toolkit.runtime import AgentRuntime
from strands.hooks import BeforeToolCallEvent


def _event(tool_name: str, command: str | list[object]) -> BeforeToolCallEvent:
    return BeforeToolCallEvent(
        agent=object(),
        selected_tool=None,
        tool_use={
            "name": tool_name,
            "input": {"command": command},
            "toolUseId": "tool-1",
        },
        invocation_state={},
    )


def test_plan_mode_settings_disabled_by_default() -> None:
    settings = PlanModeSettings.from_metadata({})
    assert not settings.enabled
    assert settings.shell_allowlist == ()


def test_plan_mode_settings_defaults_when_enabled() -> None:
    settings = PlanModeSettings.from_metadata({"plan_mode": {"enabled": True}})
    assert settings.enabled
    assert settings.shell_allowlist == DEFAULT_SHELL_ALLOWLIST


def test_plan_mode_hook_blocks_unapproved_shell_command() -> None:
    settings = PlanModeSettings(enabled=True, shell_allowlist=("ls",))
    hook = PlanModeHook(settings)
    event = _event("shell", "rm -rf /")
    hook.enforce(event)
    assert event.cancel_tool


def test_plan_mode_hook_allows_shell_command() -> None:
    settings = PlanModeSettings(enabled=True, shell_allowlist=("ls",))
    hook = PlanModeHook(settings)
    event = _event("shell", "ls -la")
    hook.enforce(event)
    assert event.cancel_tool is False


def test_plan_mode_hook_ignores_other_tools() -> None:
    settings = PlanModeSettings(enabled=True, shell_allowlist=("ls",))
    hook = PlanModeHook(settings)
    event = _event("current_time", "ls -la")
    hook.enforce(event)
    assert event.cancel_tool is False


def test_runtime_adds_plan_mode_hook(monkeypatch) -> None:
    profile = AgentProfile(
        name="plan_mode_test",
        description="Plan mode test",
        model="",
        system_prompt="",
        tools=[],
        tool_groups=[],
        extends="",
        metadata={"plan_mode": {"enabled": True, "allowed_shell": ["ls"]}},
        constraints={},
    )

    def fake_load_profiles(*_args, **_kwargs):
        return {"plan_mode_test": profile}

    monkeypatch.setattr("agent_toolkit.runtime.load_profiles", fake_load_profiles)

    runtime = AgentRuntime()

    captured: dict[str, object] = {}

    def fake_create_from_profile(self, *_args, **kwargs):
        captured["hooks"] = kwargs.get("hooks")
        return object()

    monkeypatch.setattr(AgentFactory, "create_from_profile", fake_create_from_profile)

    runtime.create_agent("plan_mode_test", session_id="test")

    hooks = captured.get("hooks") or []
    assert any(isinstance(hook, PlanModeHook) for hook in hooks)
