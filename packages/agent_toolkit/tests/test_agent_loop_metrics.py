"""Tests for agent loop metrics capture and formatting."""

from agent_toolkit.metrics import AgentLoopMetrics, extract_metrics_from_event


class MockEventLoopMetrics:
    """Mock Strands EventLoopMetrics for testing."""

    def __init__(self, summary: dict):
        self._summary = summary

    def get_summary(self) -> dict:
        return self._summary


class MockAgentResult:
    """Mock Strands AgentResult for testing."""

    def __init__(self, stop_reason: str, metrics_summary: dict):
        self.stop_reason = stop_reason
        self.metrics = MockEventLoopMetrics(metrics_summary)


def test_from_agent_result_extracts_all_fields() -> None:
    """Test that all fields are correctly extracted from AgentResult."""
    summary = {
        "total_cycles": 3,
        "accumulated_usage": {
            "inputTokens": 150,
            "outputTokens": 89,
            "totalTokens": 239,
        },
        "accumulated_metrics": {
            "latencyMs": 1234,
        },
        "tool_usage": {
            "search": {"call_count": 2, "success_rate": 1.0, "average_time": 0.5},
            "fetch": {"call_count": 1, "success_rate": 1.0, "average_time": 0.3},
        },
    }
    result = MockAgentResult(stop_reason="end_turn", metrics_summary=summary)

    metrics = AgentLoopMetrics.from_agent_result(result)

    assert metrics.total_cycles == 3
    assert metrics.input_tokens == 150
    assert metrics.output_tokens == 89
    assert metrics.total_tokens == 239
    assert metrics.total_duration_ms == 1234
    assert metrics.stop_reason == "end_turn"
    assert metrics.tool_stats["search"]["call_count"] == 2
    assert metrics.tool_stats["fetch"]["call_count"] == 1


def test_from_agent_result_handles_empty_summary() -> None:
    """Test graceful handling of empty metrics summary."""
    result = MockAgentResult(stop_reason="max_tokens", metrics_summary={})

    metrics = AgentLoopMetrics.from_agent_result(result)

    assert metrics.total_cycles == 0
    assert metrics.input_tokens == 0
    assert metrics.output_tokens == 0
    assert metrics.total_tokens == 0
    assert metrics.total_duration_ms == 0
    assert metrics.stop_reason == "max_tokens"
    assert metrics.tool_stats == {}


def test_to_dict_and_from_dict_roundtrip() -> None:
    """Test serialization roundtrip."""
    original = AgentLoopMetrics(
        total_cycles=2,
        total_duration_ms=500,
        input_tokens=100,
        output_tokens=50,
        total_tokens=150,
        stop_reason="end_turn",
        tool_stats={"calc": {"call_count": 1}},
    )

    data = original.to_dict()
    restored = AgentLoopMetrics.from_dict(data)

    assert restored.total_cycles == original.total_cycles
    assert restored.input_tokens == original.input_tokens
    assert restored.output_tokens == original.output_tokens
    assert restored.stop_reason == original.stop_reason
    assert restored.tool_stats == original.tool_stats


def test_from_dict_handles_missing_fields() -> None:
    """Test that from_dict provides defaults for missing fields."""
    data = {"total_cycles": 1}

    metrics = AgentLoopMetrics.from_dict(data)

    assert metrics.total_cycles == 1
    assert metrics.input_tokens == 0
    assert metrics.output_tokens == 0
    assert metrics.stop_reason == "unknown"
    assert metrics.tool_stats == {}


def test_format_summary_produces_readable_output() -> None:
    """Test human-readable summary formatting."""
    metrics = AgentLoopMetrics(
        total_cycles=2,
        total_duration_ms=1500,
        input_tokens=150,
        output_tokens=89,
        total_tokens=239,
        stop_reason="end_turn",
        tool_stats={},
    )

    summary = metrics.format_summary()

    assert "150 in" in summary
    assert "89 out" in summary
    assert "Cycles: 2" in summary
    assert "1.5s" in summary


def test_format_tool_summary_lists_tools() -> None:
    """Test tool usage summary formatting."""
    metrics = AgentLoopMetrics(
        total_cycles=1,
        total_duration_ms=100,
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        stop_reason="end_turn",
        tool_stats={
            "search": {"call_count": 3},
            "fetch": {"call_count": 2},
        },
    )

    summary = metrics.format_tool_summary()

    assert "search (3)" in summary
    assert "fetch (2)" in summary


def test_format_tool_summary_handles_no_tools() -> None:
    """Test tool summary when no tools were called."""
    metrics = AgentLoopMetrics(
        total_cycles=1,
        total_duration_ms=100,
        input_tokens=10,
        output_tokens=5,
        total_tokens=15,
        stop_reason="end_turn",
        tool_stats={},
    )

    summary = metrics.format_tool_summary()

    assert summary == "Tools: none"


def test_extract_metrics_from_event_with_result() -> None:
    """Test extracting metrics from a streaming event with AgentResult."""
    summary = {
        "total_cycles": 1,
        "accumulated_usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        "accumulated_metrics": {"latencyMs": 100},
        "tool_usage": {},
    }
    result = MockAgentResult(stop_reason="end_turn", metrics_summary=summary)
    event = {"result": result}

    metrics = extract_metrics_from_event(event)

    assert metrics is not None
    assert metrics.total_cycles == 1
    assert metrics.stop_reason == "end_turn"


def test_extract_metrics_from_event_without_result() -> None:
    """Test that non-result events return None."""
    event = {"data": "some text chunk"}

    metrics = extract_metrics_from_event(event)

    assert metrics is None


def test_extract_metrics_from_event_with_invalid_result() -> None:
    """Test handling of event with invalid result object."""
    event = {"result": "not an AgentResult"}

    metrics = extract_metrics_from_event(event)

    assert metrics is None
