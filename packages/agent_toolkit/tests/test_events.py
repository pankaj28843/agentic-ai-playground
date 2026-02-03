from __future__ import annotations

from dataclasses import dataclass

from agent_toolkit.events import (
    MULTIAGENT_EVENT_TYPES,
    AgentEvent,
    normalize_strands_event,
    normalize_strands_events,
)


@dataclass
class FakeMetrics:
    summary: dict

    def get_summary(self) -> dict:
        return self.summary


@dataclass
class FakeResult:
    metrics: FakeMetrics
    stop_reason: str


def test_multiagent_event_is_passed_through() -> None:
    event = {"type": "multiagent_node_start", "node_id": "node-1"}
    events = normalize_strands_event(event)
    assert len(events) == 1
    assert events[0].kind == "multiagent"
    assert events[0].subtype == "multiagent_node_start"
    assert events[0].raw == event


def test_lifecycle_init_start_complete_and_force_stop() -> None:
    init_event = {"init_event_loop": True}
    start_event = {"start_event_loop": True}
    force_event = {"force_stop": True, "force_stop_reason": "timeout"}
    complete_event = {"complete": True}

    init_events = normalize_strands_event(init_event)
    assert init_events[0].kind == "lifecycle"
    assert init_events[0].subtype == "init"

    start_events = normalize_strands_event(start_event)
    assert start_events[0].kind == "lifecycle"
    assert start_events[0].subtype == "start"

    force_events = normalize_strands_event(force_event)
    assert any(e.subtype == "force_stop" for e in force_events)
    assert any(e.payload == {"reason": "timeout"} for e in force_events)

    complete_events = normalize_strands_event(complete_event)
    assert complete_events[0].kind == "lifecycle"
    assert complete_events[0].subtype == "complete"


def test_text_reasoning_and_tool_events() -> None:
    event = {
        "data": "hello",
        "reasoning": True,
        "reasoningText": "thinking",
        "current_tool_use": {"name": "search", "input": {"q": "x"}},
    }
    events = normalize_strands_event(event)
    kinds = {e.kind for e in events}
    assert "text" in kinds
    assert "reasoning" in kinds
    assert "tool" in kinds


def test_tool_stream_event() -> None:
    event = {"tool_stream_event": {"data": "partial"}}
    events = normalize_strands_event(event)
    assert any(e.kind == "tool_stream" for e in events)


def test_metrics_event_from_result() -> None:
    summary = {
        "total_cycles": 2,
        "accumulated_usage": {"inputTokens": 10, "outputTokens": 5, "totalTokens": 15},
        "accumulated_metrics": {"latencyMs": 123},
        "tool_usage": {"search": {"call_count": 1}},
    }
    result = FakeResult(metrics=FakeMetrics(summary), stop_reason="end_turn")
    event = {"result": result}
    events = normalize_strands_event(event)
    metrics_events = [e for e in events if e.kind == "metrics"]
    assert len(metrics_events) == 1
    assert metrics_events[0].payload["total_cycles"] == 2
    assert metrics_events[0].subtype == "end_turn"


def test_unknown_event_fallback() -> None:
    events = normalize_strands_event({})
    assert len(events) == 1
    assert events[0].kind == "unknown"


def test_normalize_strands_events_flattens() -> None:
    events = normalize_strands_events(
        [
            {"data": "a"},
            {"type": "multiagent_node_stop"},
        ]
    )
    assert any(e.kind == "text" for e in events)
    assert any(e.kind == "multiagent" for e in events)
    assert set(MULTIAGENT_EVENT_TYPES).issuperset({"multiagent_node_stop"})


def test_agent_event_envelope_is_immutable() -> None:
    event = AgentEvent(kind="text", raw={"data": "x"})
    assert event.kind == "text"
