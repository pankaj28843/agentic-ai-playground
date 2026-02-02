"""Tests for execution strategies.

Reference: Clean Code Chapter 9 - Unit Tests
- F.I.R.S.T. principles applied
- Domain-specific test language
"""

import pytest
from agent_toolkit.execution import (
    ExecutionContext,
    ExecutionResult,
    ExecutionStrategy,
    GraphStrategy,
    SingleAgentStrategy,
    SwarmStrategy,
)
from agent_toolkit.stream_utils import OutputAccumulator


class MockAgent:
    """Mock agent for testing single agent strategy."""

    def __init__(self, events: list[dict]):
        self._events = events
        self.messages: list[dict] = []

    async def stream_async(self, prompt: str):
        for event in self._events:
            yield event


class MockSwarm:
    """Mock swarm for testing swarm strategy."""

    def __init__(self, events: list[dict]):
        self._events = events

    async def stream_async(self, prompt: str, invocation_state: dict):
        for event in self._events:
            yield event


class MockGraph:
    """Mock graph for testing graph strategy."""

    def __init__(self, events: list[dict] | None = None, result: str = ""):
        self._events = events
        self._result = result

    async def stream_async(self, prompt: str, invocation_state: dict):
        if self._events:
            for event in self._events:
                yield event

    async def invoke_async(self, prompt: str, invocation_state: dict):
        return self._result


# --- Single Agent Strategy Tests ---


@pytest.mark.asyncio
async def test_single_agent_streams_text_events() -> None:
    """Single agent strategy yields text events from agent."""
    events = [{"data": "Hello "}, {"data": "world!"}]
    agent = MockAgent(events)
    strategy = SingleAgentStrategy(agent)
    accumulator = OutputAccumulator()

    collected = [e async for e in strategy.stream("test", accumulator)]

    text_events = [e for e in collected if "data" in e]
    assert len(text_events) == 2
    assert accumulator.get_output() == "Hello world!"


@pytest.mark.asyncio
async def test_single_agent_streams_tool_events() -> None:
    """Single agent strategy yields tool use events."""
    events = [{"current_tool_use": {"name": "search", "input": {}}}]
    agent = MockAgent(events)
    strategy = SingleAgentStrategy(agent)
    accumulator = OutputAccumulator()

    collected = [e async for e in strategy.stream("test", accumulator)]

    tool_events = [e for e in collected if "current_tool_use" in e]
    assert len(tool_events) == 1
    assert tool_events[0]["current_tool_use"]["name"] == "search"


@pytest.mark.asyncio
async def test_single_agent_injects_history() -> None:
    """Single agent strategy injects history messages."""
    events = [{"data": "response"}]
    agent = MockAgent(events)
    history = [{"role": "user", "content": [{"text": "previous"}]}]
    strategy = SingleAgentStrategy(agent, history_messages=history)
    accumulator = OutputAccumulator()

    _ = [e async for e in strategy.stream("test", accumulator)]

    assert len(agent.messages) == 1
    assert agent.messages[0]["role"] == "user"


# --- Swarm Strategy Tests ---


@pytest.mark.asyncio
async def test_swarm_streams_events() -> None:
    """Swarm strategy yields events from swarm execution."""
    events = [{"data": "Swarm response"}]
    swarm = MockSwarm(events)
    strategy = SwarmStrategy(swarm)
    accumulator = OutputAccumulator()

    collected = [e async for e in strategy.stream("test", accumulator)]

    text_events = [e for e in collected if "data" in e]
    assert len(text_events) == 1
    assert text_events[0]["data"] == "Swarm response"


@pytest.mark.asyncio
async def test_swarm_passes_invocation_state() -> None:
    """Swarm strategy passes invocation state to swarm."""
    received_state: dict = {}

    class StateCapturingSwarm:
        async def stream_async(self, prompt: str, invocation_state: dict):
            nonlocal received_state
            received_state = invocation_state
            yield {"data": "done"}

    swarm = StateCapturingSwarm()
    strategy = SwarmStrategy(swarm)
    state = {"resource_uri": "test://resource"}
    accumulator = OutputAccumulator()

    _ = [e async for e in strategy.stream("test", accumulator, invocation_state=state)]

    assert received_state == state


# --- Graph Strategy Tests ---


@pytest.mark.asyncio
async def test_graph_streams_events_when_available() -> None:
    """Graph strategy yields events when stream_async is available."""
    events = [{"data": "Graph output"}]
    graph = MockGraph(events=events)
    strategy = GraphStrategy(graph)
    accumulator = OutputAccumulator()

    collected = [e async for e in strategy.stream("test", accumulator)]

    text_events = [e for e in collected if "data" in e]
    assert len(text_events) >= 1


@pytest.mark.asyncio
async def test_graph_falls_back_to_invoke() -> None:
    """Graph strategy falls back to invoke_async when no stream_async."""

    class InvokeOnlyGraph:
        async def invoke_async(self, prompt: str, invocation_state: dict):
            return "Fallback result"

    graph = InvokeOnlyGraph()
    strategy = GraphStrategy(graph)
    accumulator = OutputAccumulator()

    collected = [e async for e in strategy.stream("test", accumulator)]

    # Should have a completion event with the result
    complete_events = [e for e in collected if e.get("complete")]
    assert len(complete_events) == 1


# --- ExecutionResult Tests ---


def test_execution_result_defaults() -> None:
    """ExecutionResult has sensible defaults."""
    result = ExecutionResult(output="test", tool_events=[])
    assert result.trace_id is None
    assert result.metrics is None


def test_execution_result_with_all_fields() -> None:
    """ExecutionResult accepts all fields."""
    events = [{"name": "tool1", "input": "", "output": "", "ts": ""}]
    result = ExecutionResult(
        output="output",
        tool_events=events,
        trace_id="trace-123",
        metrics={"total_cycles": 1},
    )
    assert result.output == "output"
    assert len(result.tool_events) == 1
    assert result.trace_id == "trace-123"
    assert result.metrics["total_cycles"] == 1


# --- Strategy Pattern Tests ---


def test_all_strategies_inherit_from_base() -> None:
    """All strategies properly inherit from ExecutionStrategy."""
    assert issubclass(SingleAgentStrategy, ExecutionStrategy)
    assert issubclass(SwarmStrategy, ExecutionStrategy)
    assert issubclass(GraphStrategy, ExecutionStrategy)


# --- ExecutionContext Tests ---


def test_execution_context_effective_session_id_uses_provided() -> None:
    """ExecutionContext uses provided session_id when available."""
    ctx = ExecutionContext(
        mode="single",
        profile_name="test",
        session_id="my-session",
    )
    assert ctx.effective_session_id() == "my-session"


def test_execution_context_effective_session_id_generates_default() -> None:
    """ExecutionContext generates default session_id from mode and profile."""
    ctx = ExecutionContext(
        mode="swarm",
        profile_name="researcher",
        session_id="",
    )
    assert ctx.effective_session_id() == "swarm-researcher"


def test_execution_context_resource_uri_from_state() -> None:
    """ExecutionContext extracts resource_uri from invocation state."""
    ctx = ExecutionContext(
        mode="single",
        profile_name="test",
        session_id="session-1",
        invocation_state={"resource_uri": "file:///path/to/resource"},
    )
    assert ctx.resource_uri == "file:///path/to/resource"


def test_execution_context_resource_uri_default() -> None:
    """ExecutionContext returns empty string when no resource_uri."""
    ctx = ExecutionContext(
        mode="single",
        profile_name="test",
        session_id="session-1",
    )
    assert ctx.resource_uri == ""
