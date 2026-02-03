from __future__ import annotations

from assistant_web_backend.services.streaming import StreamState


def test_stream_state_truncates_tool_result() -> None:
    state = StreamState()
    tool_id = "tool-1"

    state.handle_event({"current_tool_use": {"toolUseId": tool_id, "name": "shell", "input": {}}})
    state.handle_event({"toolUseId": tool_id, "tool_result": "x" * 3000})

    tool = state.tool_calls[tool_id]
    assert tool.result_truncated is True
    assert tool.result_full is not None
    assert len(str(tool.result)) <= 2000
