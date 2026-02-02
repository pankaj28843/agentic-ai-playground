"""Tests for streaming event normalization."""

import pytest
from agent_toolkit.streaming import StreamChunk, stream_agent


class MockEventLoopMetrics:
    """Mock EventLoopMetrics for testing."""

    def __init__(self, summary: dict):
        self._summary = summary

    def get_summary(self) -> dict:
        return self._summary


class MockAgentResult:
    """Mock AgentResult for testing."""

    def __init__(self, stop_reason: str, metrics_summary: dict):
        self.stop_reason = stop_reason
        self.metrics = MockEventLoopMetrics(metrics_summary)


class MockAgent:
    """Mock Strands agent for testing streaming."""

    def __init__(self, events: list[dict]):
        self._events = events

    async def stream_async(self, prompt: str):
        for event in self._events:
            yield event


@pytest.mark.asyncio
async def test_stream_agent_emits_text_chunks() -> None:
    """Test that text data events become text chunks."""
    events = [
        {"data": "Hello "},
        {"data": "world!"},
        {"complete": True},
    ]
    agent = MockAgent(events)

    chunks = [chunk async for chunk in stream_agent(agent, "test")]

    text_chunks = [c for c in chunks if c.kind == "text"]
    assert len(text_chunks) == 2
    assert text_chunks[0].data == "Hello "
    assert text_chunks[1].data == "world!"


@pytest.mark.asyncio
async def test_stream_agent_emits_tool_chunks() -> None:
    """Test that tool use events become tool chunks."""
    events = [
        {"current_tool_use": {"name": "search", "input": {"query": "test"}}},
        {"complete": True},
    ]
    agent = MockAgent(events)

    chunks = [chunk async for chunk in stream_agent(agent, "test")]

    tool_chunks = [c for c in chunks if c.kind == "tool"]
    assert len(tool_chunks) == 1
    assert tool_chunks[0].data["name"] == "search"


@pytest.mark.asyncio
async def test_stream_agent_ignores_empty_tool_use() -> None:
    """Test that empty tool use events are ignored."""
    events = [
        {"current_tool_use": {}},
        {"current_tool_use": None},
        {"complete": True},
    ]
    agent = MockAgent(events)

    chunks = [chunk async for chunk in stream_agent(agent, "test")]

    tool_chunks = [c for c in chunks if c.kind == "tool"]
    assert len(tool_chunks) == 0


@pytest.mark.asyncio
async def test_stream_agent_emits_cycle_start() -> None:
    """Test that start_event_loop events become cycle_start chunks."""
    events = [
        {"start_event_loop": True},
        {"data": "text"},
        {"complete": True},
    ]
    agent = MockAgent(events)

    chunks = [chunk async for chunk in stream_agent(agent, "test")]

    cycle_chunks = [c for c in chunks if c.kind == "cycle_start"]
    assert len(cycle_chunks) == 1


@pytest.mark.asyncio
async def test_stream_agent_emits_complete_with_stop_reason() -> None:
    """Test that complete events have stop_reason."""
    events = [{"complete": True}]
    agent = MockAgent(events)

    chunks = [chunk async for chunk in stream_agent(agent, "test")]

    complete_chunks = [c for c in chunks if c.kind == "complete"]
    assert len(complete_chunks) == 1
    assert complete_chunks[0].stop_reason == "end_turn"


@pytest.mark.asyncio
async def test_stream_agent_emits_force_stop() -> None:
    """Test that force_stop events become force_stop chunks."""
    events = [{"force_stop": True, "force_stop_reason": "max_tokens"}]
    agent = MockAgent(events)

    chunks = [chunk async for chunk in stream_agent(agent, "test")]

    stop_chunks = [c for c in chunks if c.kind == "force_stop"]
    assert len(stop_chunks) == 1
    assert stop_chunks[0].stop_reason == "max_tokens"


@pytest.mark.asyncio
async def test_stream_agent_emits_metrics_chunk() -> None:
    """Test that AgentResult events become metrics chunks."""
    summary = {
        "total_cycles": 2,
        "accumulated_usage": {"inputTokens": 100, "outputTokens": 50, "totalTokens": 150},
        "accumulated_metrics": {"latencyMs": 500},
        "tool_usage": {},
    }
    result = MockAgentResult(stop_reason="end_turn", metrics_summary=summary)
    events = [{"result": result}]
    agent = MockAgent(events)

    chunks = [chunk async for chunk in stream_agent(agent, "test")]

    metrics_chunks = [c for c in chunks if c.kind == "metrics"]
    assert len(metrics_chunks) == 1
    assert metrics_chunks[0].stop_reason == "end_turn"
    assert metrics_chunks[0].metrics is not None
    assert metrics_chunks[0].metrics["total_cycles"] == 2
    assert metrics_chunks[0].metrics["input_tokens"] == 100


def test_stream_chunk_defaults() -> None:
    """Test StreamChunk default values."""
    chunk = StreamChunk(kind="text", data="hello")
    assert chunk.stop_reason is None
    assert chunk.metrics is None


def test_stream_chunk_with_metrics() -> None:
    """Test StreamChunk with all fields."""
    metrics = {"total_cycles": 1, "input_tokens": 10}
    chunk = StreamChunk(
        kind="metrics",
        data={},
        stop_reason="end_turn",
        metrics=metrics,
    )
    assert chunk.kind == "metrics"
    assert chunk.stop_reason == "end_turn"
    assert chunk.metrics["total_cycles"] == 1
