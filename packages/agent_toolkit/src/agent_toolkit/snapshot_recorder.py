"""Snapshot recording for agent runs.

Consolidates run snapshot creation and persistence logic.
Follows Single Responsibility Principle - one reason to change.

Reference: 12-Factor Agents - Factor 9 (Compact Logs, Rich Telemetry)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_toolkit.run_history import RunSnapshot, write_snapshot
from agent_toolkit.stream_utils import format_tool_input
from agent_toolkit.utils import utc_timestamp

if TYPE_CHECKING:
    from agent_toolkit.hooks import ToolTelemetry


def record_run_snapshot(
    run_id: str,
    mode: str,
    profile: str,
    session_id: str,
    resource_uri: str,
    prompt: str,
    output: str,
    tool_events: list[dict[str, str]],
    started_at: str,
    metrics: dict | None = None,
) -> None:
    """Record a run snapshot to persistent storage.

    Args:
        run_id: Unique identifier for this run
        mode: Execution mode (single, graph, swarm)
        profile: Agent profile name
        session_id: Session identifier
        resource_uri: Optional resource URI
        prompt: User prompt that triggered the run
        output: Final output (truncated to 2000 chars)
        tool_events: List of tool invocation events
        started_at: ISO timestamp when run started
        metrics: Optional metrics dictionary
    """
    snapshot = RunSnapshot(
        run_id=run_id,
        mode=mode,
        profile=profile,
        session_id=session_id,
        resource_uri=resource_uri,
        prompt=prompt,
        output=output[:2000],
        tool_events=tool_events,
        started_at=started_at,
        finished_at=utc_timestamp(),
        metrics=metrics,
    )
    write_snapshot(snapshot)


def build_tool_events_from_telemetry(telemetry: ToolTelemetry) -> list[dict[str, str]]:
    """Convert telemetry tool calls to event format.

    Args:
        telemetry: ToolTelemetry instance with recorded calls

    Returns:
        List of tool event dictionaries with name, input, output, ts fields
    """
    timestamp = utc_timestamp()
    tool_events: list[dict[str, str]] = []
    for call in telemetry.tool_calls:
        name = str(call.get("name", "unknown"))
        input_payload = call.get("arguments", {})
        tool_events.append(
            {
                "name": name,
                "input": format_tool_input(input_payload),
                "output": "",
                "ts": timestamp,
            }
        )
    return tool_events
