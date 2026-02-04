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


def test_stream_state_handles_tool_stream_event() -> None:
    state = StreamState()
    tool_id = "tool-stream"

    state.handle_event({"current_tool_use": {"toolUseId": tool_id, "name": "search", "input": {}}})
    state.handle_event(
        {
            "tool_stream_event": {
                "tool_use": {"toolUseId": tool_id, "name": "search"},
                "data": {"partial": True},
            }
        }
    )

    tool = state.tool_calls[tool_id]
    assert tool.status is not None
    assert tool.status.type == "running"
    assert tool.result is not None
    assert "partial" in str(tool.result)


def test_stream_state_handles_tool_result_in_multiagent_stream() -> None:
    state = StreamState()
    tool_id = "tool-multi"

    state.handle_event({"type": "multiagent_node_start", "node_id": "agent-1"})
    state.handle_event(
        {
            "type": "multiagent_node_stream",
            "node_id": "agent-1",
            "event": {
                "current_tool_use": {
                    "toolUseId": tool_id,
                    "name": "search",
                    "input": {"q": "test"},
                }
            },
        }
    )
    state.handle_event(
        {
            "type": "multiagent_node_stream",
            "node_id": "agent-1",
            "event": {
                "type": "tool_result",
                "toolUseId": tool_id,
                "content": {"ok": True},
            },
        }
    )

    tool = state.tool_calls[tool_id]
    assert tool.result is not None
    assert "ok" in str(tool.result)


def test_stream_state_handles_tool_result_from_multiagent_message() -> None:
    state = StreamState()
    tool_id = "tool-msg"

    state.handle_event({"type": "multiagent_node_start", "node_id": "agent-2"})
    state.handle_event(
        {
            "type": "multiagent_node_stream",
            "node_id": "agent-2",
            "event": {
                "current_tool_use": {
                    "toolUseId": tool_id,
                    "name": "fetch",
                    "input": {"url": "https://example.com"},
                }
            },
        }
    )
    state.handle_event(
        {
            "type": "multiagent_node_stream",
            "node_id": "agent-2",
            "event": {
                "message": {
                    "role": "user",
                    "content": [
                        {
                            "toolResult": {
                                "toolUseId": tool_id,
                                "content": {"status": "ok"},
                            }
                        }
                    ],
                }
            },
        }
    )

    tool = state.tool_calls[tool_id]
    assert tool.result is not None
    assert "ok" in str(tool.result)


def test_stream_state_handles_tool_use_from_multiagent_message() -> None:
    state = StreamState()
    tool_id = "tool-use-msg"

    state.handle_event({"type": "multiagent_node_start", "node_id": "agent-3"})
    state.handle_event(
        {
            "type": "multiagent_node_stream",
            "node_id": "agent-3",
            "event": {
                "message": {
                    "role": "assistant",
                    "content": [
                        {
                            "toolUse": {
                                "toolUseId": tool_id,
                                "name": "search",
                                "input": {"q": "docs"},
                            }
                        }
                    ],
                }
            },
        }
    )

    assert tool_id in state.tool_calls
    assert state.tool_calls[tool_id].tool_name == "search"
