"""Hooks package for agent lifecycle and tool execution.

Provides hook providers for extending agent behavior:
- ToolTelemetryHook: Tracks tool usage for run snapshots
- ToolApprovalHook: Requires user approval for sensitive tools
- TechDocsWorkflowHook: Enforces proper TechDocs tool workflow

Hooks follow the Strands HookProvider pattern: register callbacks
that respond to lifecycle events (BeforeInvocation, BeforeToolCall, etc.).

12-Factor Agents Reference:
- Factor 7: Contact Humans with Tool Calls (approval workflow)
"""

from agent_toolkit.hooks.approval import ToolApprovalHook
from agent_toolkit.hooks.techdocs import TechDocsWorkflowHook
from agent_toolkit.hooks.telemetry import ToolTelemetry, ToolTelemetryHook

__all__ = [
    "TechDocsWorkflowHook",
    "ToolApprovalHook",
    "ToolTelemetry",
    "ToolTelemetryHook",
]
