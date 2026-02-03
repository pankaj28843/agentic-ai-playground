"""Accumulator utilities for streaming events.

Handles output buffering and tool event collection during agent streaming.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agent_toolkit.tools.truncation import truncate_text
from agent_toolkit.utils import utc_timestamp


@dataclass
class OutputAccumulator:
    """Accumulates output and tool events during streaming.

    Used by execution strategies to track streaming state and build
    run snapshots after execution completes.
    """

    output_buffer: list[str] = field(default_factory=list)
    tool_events: list[dict[str, Any]] = field(default_factory=list)

    def add_output(self, event: dict[str, Any]) -> None:
        """Add output from an event to the buffer."""
        accumulate_output(event, self.output_buffer)

    def add_tool_event(self, event: dict[str, Any]) -> None:
        """Track tool execution from an event."""
        accumulate_tool_event(event, self.tool_events)

    def process_event(self, event: dict[str, Any]) -> None:
        """Process a streaming event, accumulating output and tool events."""
        self.add_output(event)
        self.add_tool_event(event)

    def get_output(self) -> str:
        """Get accumulated output as a single string."""
        return "".join(self.output_buffer)


def accumulate_output(event: dict[str, Any], buffer: list[str]) -> None:
    """Accumulate text output from a streaming event."""
    if "data" in event:
        buffer.append(str(event["data"]))


def accumulate_tool_event(event: dict[str, Any], tool_events: list[dict[str, Any]]) -> None:
    """Track tool execution from a streaming event."""
    tool_use = event.get("current_tool_use")
    if isinstance(tool_use, dict) and tool_use.get("name"):
        input_text = str(tool_use.get("input", ""))
        input_trunc = truncate_text(input_text, 200)
        tool_events.append(
            {
                "name": str(tool_use.get("name")),
                "input": input_trunc.text,
                "input_truncated": input_trunc.truncated,
                "input_length": input_trunc.original_length,
                "output": "",
                "ts": utc_timestamp(),
            }
        )
        if input_trunc.truncated:
            tool_events[-1]["input_full"] = input_text
    tool_result = event.get("tool_result") or event.get("tool_output")
    if tool_result and tool_events:
        output_text = str(tool_result)
        output_trunc = truncate_text(output_text, 500)
        tool_events[-1]["output"] = output_trunc.text
        tool_events[-1]["output_truncated"] = output_trunc.truncated
        tool_events[-1]["output_length"] = output_trunc.original_length
        if output_trunc.truncated:
            tool_events[-1]["output_full"] = output_text
