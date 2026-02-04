import pytest
from agent_toolkit.application import ExecutionPlan, ToolingBuilder
from agent_toolkit.config import get_config_service
from agent_toolkit.runtime import AgentRuntime
from agent_toolkit.tools import DEFAULT_TOOL_REGISTRY, ToolCatalog


def test_profile_overrides_apply_model_and_tool_groups() -> None:
    service = get_config_service()
    profile = next(iter(service.build_profiles().values()))
    tooling = ToolingBuilder(
        settings=service.get_settings(),
        catalog=ToolCatalog(DEFAULT_TOOL_REGISTRY, service),
    )

    updated = tooling.apply_profile_overrides(
        profile,
        model_override="bedrock.nova-pro",
        tool_groups_override=["strands_basic"],
    )

    assert updated.model == "bedrock.nova-pro"
    assert updated.tool_groups == ["strands_basic"]
    assert "strands:calculator" in updated.tools


def test_profile_overrides_noop_returns_profile() -> None:
    service = get_config_service()
    profile = next(iter(service.build_profiles().values()))
    tooling = ToolingBuilder(
        settings=service.get_settings(),
        catalog=ToolCatalog(DEFAULT_TOOL_REGISTRY, service),
    )

    updated = tooling.apply_profile_overrides(
        profile, model_override=None, tool_groups_override=None
    )

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

    monkeypatch.setattr(
        "agent_toolkit.application.execution_pipeline.build_graph", fake_build_graph
    )
    monkeypatch.setattr(
        runtime._pipeline,  # noqa: SLF001
        "resolve_plan",
        lambda _profile: ExecutionPlan("graph", "default", {}),
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

    monkeypatch.setattr(
        "agent_toolkit.application.execution_pipeline.build_swarm", fake_build_swarm
    )
    monkeypatch.setattr(
        runtime._pipeline,  # noqa: SLF001
        "resolve_plan",
        lambda _profile: ExecutionPlan("swarm", "default", {}),
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
