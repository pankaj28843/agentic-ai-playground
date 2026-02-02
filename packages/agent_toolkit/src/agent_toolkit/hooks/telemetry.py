"""Tool telemetry tracking for agent sessions.

Provides ToolTelemetry for recording tool usage and ToolTelemetryHook
for integrating with the Strands hook system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from strands.hooks import (
    BeforeInvocationEvent,
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)


@dataclass
class ToolTelemetry:
    """Track tool usage for a single agent session."""

    active_tool: str | None = None
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    allow_tools: bool = True

    def reset(self) -> None:
        """Clear tracked tool usage for a new invocation."""
        self.active_tool = None
        self.tool_calls.clear()

    def record_call(self, name: str, arguments: dict[str, Any]) -> None:
        """Record a tool invocation."""
        self.active_tool = name
        self.tool_calls.append({"name": name, "arguments": arguments})

    def set_allow_tools(self, allow: bool) -> None:
        """Enable or disable tool calls for this telemetry session."""
        self.allow_tools = allow


class ToolTelemetryHook(HookProvider):
    """Hook provider for collecting tool telemetry."""

    def __init__(self, telemetry: ToolTelemetry) -> None:
        """Attach telemetry storage to hook callbacks."""
        self._telemetry = telemetry

    def register_hooks(self, registry: HookRegistry, **_kwargs: Any) -> None:
        """Register hook callbacks for tool events."""
        registry.add_callback(BeforeInvocationEvent, self._reset)
        registry.add_callback(BeforeToolCallEvent, self._record_tool)

    def _reset(self, _event: BeforeInvocationEvent) -> None:
        """Reset telemetry at the start of each invocation."""
        self._telemetry.reset()

    def _record_tool(self, event: BeforeToolCallEvent) -> None:
        """Capture tool usage and optionally block tool calls."""
        if not self._telemetry.allow_tools:
            event.cancel_tool = "Tool calls are disabled by user confirmation settings."
            return
        tool_input = event.tool_use.get("input", {})
        self._telemetry.record_call(event.tool_use.get("name", "unknown"), tool_input)
