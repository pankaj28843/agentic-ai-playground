from agent_toolkit.stream_utils.accumulator import OutputAccumulator


def test_accumulator_unwraps_multiagent_output() -> None:
    accumulator = OutputAccumulator()
    accumulator.process_event({"type": "multiagent_node_stream", "event": {"data": "Hello"}})

    assert accumulator.get_output() == "Hello"


def test_accumulator_handles_tool_stream_event() -> None:
    accumulator = OutputAccumulator()
    accumulator.process_event({"current_tool_use": {"name": "search", "input": {"q": "test"}}})
    accumulator.process_event({"tool_stream_event": {"data": {"partial": True}}})

    assert accumulator.tool_events
    assert "partial" in accumulator.tool_events[-1]["output"]


def test_accumulator_handles_tool_result_event_type() -> None:
    accumulator = OutputAccumulator()
    accumulator.process_event({"current_tool_use": {"name": "search", "input": {"q": "test"}}})
    accumulator.process_event({"type": "tool_result", "content": {"ok": True}})

    assert accumulator.tool_events
    assert "ok" in accumulator.tool_events[-1]["output"]
