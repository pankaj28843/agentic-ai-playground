"""Tool approval workflow hook.

Provides ToolApprovalHook for interrupting tool calls that require user approval.
"""

from __future__ import annotations

from typing import Any

from strands.hooks import (
    BeforeToolCallEvent,
    HookProvider,
    HookRegistry,
)


class ToolApprovalHook(HookProvider):
    """Interrupt tool calls for user approval."""

    def __init__(self, tools: list[str], namespace: str = "agentic") -> None:
        """Initialize with an allowlist of tools requiring approval."""
        self._tools = set(tools)
        self._namespace = namespace

    def register_hooks(self, registry: HookRegistry, **_kwargs: Any) -> None:
        """Register interrupt hook for tool calls."""
        registry.add_callback(BeforeToolCallEvent, self.approve)

    def approve(self, event: BeforeToolCallEvent) -> None:
        """Raise interrupts for approval on configured tools."""
        tool_name = event.tool_use.get("name")
        if tool_name not in self._tools:
            return
        interrupt_name = f"{self._namespace}-approval"
        approval = event.interrupt(interrupt_name, reason={"tool": tool_name})
        if approval.lower() not in {"y", "yes", "allow"}:
            event.cancel_tool = "User denied tool execution"
