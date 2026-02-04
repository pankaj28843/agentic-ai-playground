from __future__ import annotations

from agent_toolkit.stream_utils.accumulator import accumulate_tool_event
from agent_toolkit.tools.truncation import truncate_lines, truncate_text


def test_truncate_text_no_truncation() -> None:
    result = truncate_text("abc", 5)
    assert not result.truncated
    assert result.text == "abc"


def test_truncate_text_truncates() -> None:
    result = truncate_text("abcdef", 4)
    assert result.truncated
    assert result.text == "a..."
    assert result.original_length == 6


def test_truncate_lines_truncates() -> None:
    text = "a\nb\nc"
    result = truncate_lines(text, 2)
    assert result.truncated
    assert result.text.startswith("a\nb")


def test_accumulate_tool_event_truncates_payloads() -> None:
    tool_events: list[dict[str, object]] = []
    event = {
        "current_tool_use": {"name": "shell", "input": "x" * 250},
        "tool_result": "y" * 600,
    }

    accumulate_tool_event(event, tool_events)

    assert len(tool_events) == 1
    entry = tool_events[0]
    assert entry["input_truncated"] is True
    assert entry["output_truncated"] is True
    assert isinstance(entry.get("input_full"), str)
    assert isinstance(entry.get("output_full"), str)
