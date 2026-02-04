from __future__ import annotations

from typing import Any

import pytest
from agent_toolkit.agents.factory import AgentFactory
from agent_toolkit.application import ExecutionPipeline, ExecutionPlan, ToolingBuilder
from agent_toolkit.config import get_config_service
from agent_toolkit.execution import ExecutionContext, ExecutionStrategy
from agent_toolkit.hooks import ToolTelemetry
from agent_toolkit.models.runtime import RuntimeAgent
from agent_toolkit.tools import DEFAULT_TOOL_REGISTRY, ToolCatalog


class _FakeAgent:
    def __call__(self, prompt: str) -> str:
        return "ok"


class _FakeStrategy(ExecutionStrategy):
    async def stream(self, prompt, accumulator, invocation_state=None):
        event = {"data": "hi", "complete": True}
        accumulator.process_event(event)
        yield event


@pytest.mark.asyncio
async def test_pipeline_stream_records_snapshot(monkeypatch) -> None:
    service = get_config_service()
    tooling = ToolingBuilder(
        settings=service.get_settings(),
        catalog=ToolCatalog(DEFAULT_TOOL_REGISTRY, service),
    )
    pipeline = ExecutionPipeline(
        config_service=service,
        factory=AgentFactory(settings=service.get_settings(), registry=DEFAULT_TOOL_REGISTRY),
        tooling=tooling,
        swarm_preset=None,
    )

    recorded: dict[str, Any] = {}

    monkeypatch.setattr(
        pipeline,
        "resolve_plan",
        lambda _profile: ExecutionPlan("single", "quick", {}),
    )
    monkeypatch.setattr(pipeline, "_build_strategy", lambda _ctx, _messages: _FakeStrategy())

    def fake_record_snapshot(**kwargs):
        recorded.update(kwargs)

    monkeypatch.setattr(
        "agent_toolkit.application.execution_pipeline.record_run_snapshot", fake_record_snapshot
    )

    ctx = ExecutionContext(
        mode="quick",
        profile_name="quick",
        session_id="session-1",
        invocation_state={},
    )

    async for _ in pipeline.stream(
        ctx,
        messages=[{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
    ):
        pass

    assert recorded.get("profile") == "quick"
    assert recorded.get("session_id") == "session-1"
    assert recorded.get("output") == "hi"


def test_pipeline_run_records_snapshot(monkeypatch) -> None:
    service = get_config_service()
    tooling = ToolingBuilder(
        settings=service.get_settings(),
        catalog=ToolCatalog(DEFAULT_TOOL_REGISTRY, service),
    )
    pipeline = ExecutionPipeline(
        config_service=service,
        factory=AgentFactory(settings=service.get_settings(), registry=DEFAULT_TOOL_REGISTRY),
        tooling=tooling,
        swarm_preset=None,
    )

    recorded: dict[str, Any] = {}

    monkeypatch.setattr(
        pipeline,
        "resolve_plan",
        lambda _profile: ExecutionPlan("single", "quick", {}),
    )

    def fake_create_agent(*_args, **_kwargs):
        return RuntimeAgent(profile=None, agent=_FakeAgent(), telemetry=ToolTelemetry())

    monkeypatch.setattr(pipeline, "create_agent", fake_create_agent)

    def fake_record_snapshot(**kwargs):
        recorded.update(kwargs)

    monkeypatch.setattr(
        "agent_toolkit.application.execution_pipeline.record_run_snapshot", fake_record_snapshot
    )

    ctx = ExecutionContext(
        mode="quick",
        profile_name="quick",
        session_id="session-2",
        invocation_state={},
    )

    result = pipeline.run(ctx, "Hello")

    assert result == "ok"
    assert recorded.get("profile") == "quick"
    assert recorded.get("session_id") == "session-2"
