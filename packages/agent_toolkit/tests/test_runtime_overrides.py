import pytest
from agent_toolkit.runtime import AgentRuntime


def test_profile_overrides_apply_model_and_tool_groups() -> None:
    runtime = AgentRuntime()
    profile = runtime.list_profiles()[0]

    updated = runtime.apply_profile_overrides(
        profile,
        model_override="bedrock.nova-pro",
        tool_groups_override=["strands_basic"],
    )

    assert updated.model == "bedrock.nova-pro"
    assert updated.tool_groups == ["strands_basic"]
    assert "strands:calculator" in updated.tools


def test_profile_overrides_noop_returns_profile() -> None:
    runtime = AgentRuntime()
    profile = runtime.list_profiles()[0]

    updated = runtime.apply_profile_overrides(profile, None, None)

    assert updated is profile


@pytest.mark.asyncio
async def test_runtime_stream_passes_graph_overrides(monkeypatch) -> None:
    runtime = AgentRuntime()
    captured: dict[str, object] = {}

    class DummyGraph:
        async def stream_async(self, prompt, invocation_state=None):
            if False:
                yield prompt

    def fake_build_graph(*args, **kwargs):
        captured["model_override"] = kwargs.get("model_override")
        captured["tool_groups_override"] = kwargs.get("tool_groups_override")
        return DummyGraph()

    monkeypatch.setattr("agent_toolkit.runtime.build_graph", fake_build_graph)

    mode_resolver = runtime._mode_resolver  # noqa: SLF001
    monkeypatch.setattr(
        mode_resolver,
        "resolve_execution_mode",
        lambda _profile: ("graph", "default", {}),
    )

    async for _ in runtime.stream(
        mode="quick",
        profile_name="quick",
        messages=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
        invocation_state={},
        session_id="session-1",
        model_override="bedrock.nova-pro",
        tool_groups_override=["strands_basic"],
    ):
        pass

    assert captured["model_override"] == "bedrock.nova-pro"
    assert captured["tool_groups_override"] == ["strands_basic"]


@pytest.mark.asyncio
async def test_runtime_stream_passes_swarm_overrides(monkeypatch) -> None:
    runtime = AgentRuntime()
    captured: dict[str, object] = {}

    class DummySwarm:
        async def stream_async(self, prompt, invocation_state=None):
            if False:
                yield prompt

    def fake_build_swarm(*args, **kwargs):
        captured["model_override"] = kwargs.get("model_override")
        captured["tool_groups_override"] = kwargs.get("tool_groups_override")
        return DummySwarm()

    monkeypatch.setattr("agent_toolkit.runtime.build_swarm", fake_build_swarm)

    mode_resolver = runtime._mode_resolver  # noqa: SLF001
    monkeypatch.setattr(
        mode_resolver,
        "resolve_execution_mode",
        lambda _profile: ("swarm", "default", {}),
    )

    async for _ in runtime.stream(
        mode="quick",
        profile_name="quick",
        messages=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
        invocation_state={},
        session_id="session-2",
        model_override="bedrock.nova-pro",
        tool_groups_override=["strands_basic"],
    ):
        pass

    assert captured["model_override"] == "bedrock.nova-pro"
    assert captured["tool_groups_override"] == ["strands_basic"]
