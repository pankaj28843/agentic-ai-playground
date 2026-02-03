"""Unified event schema for agent streaming.

Provides a normalized event envelope over raw Strands events.
This module keeps raw event data available while exposing a stable
`kind` classification for downstream consumers (UI, logging, tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Iterable

from agent_toolkit.metrics import extract_metrics_from_event

EventKind = Literal[
    "lifecycle",
    "text",
    "tool",
    "tool_stream",
    "reasoning",
    "metrics",
    "multiagent",
    "unknown",
]

MULTIAGENT_EVENT_TYPES: set[str] = {
    "multiagent_node_start",
    "multiagent_node_stream",
    "multiagent_node_stop",
    "multiagent_handoff",
    "multiagent_result",
}


@dataclass(frozen=True)
class AgentEvent:
    """Normalized agent event envelope.

    Attributes:
        kind: High-level classification for consumers.
        raw: The original event payload (unchanged).
        payload: Optional normalized payload for convenience.
        subtype: Optional sub-classification (e.g., lifecycle subtype).
    """

    kind: EventKind
    raw: dict[str, Any]
    payload: dict[str, Any] | None = None
    subtype: str | None = None


def normalize_strands_event(event: dict[str, Any]) -> list[AgentEvent]:
    """Normalize a single Strands event into one or more AgentEvent entries.

    Strands events can include multiple signals (e.g., text + tool use).
    This function emits a separate AgentEvent for each major signal so
    downstream consumers can handle them deterministically.
    """
    events: list[AgentEvent] = []

    event_type = str(event.get("type", ""))
    if event_type in MULTIAGENT_EVENT_TYPES:
        events.append(AgentEvent(kind="multiagent", raw=event, subtype=event_type))
        return events

    # Lifecycle markers
    if event.get("init_event_loop") or event.get("start_event_loop"):
        subtype = "init" if event.get("init_event_loop") else "start"
        events.append(AgentEvent(kind="lifecycle", raw=event, subtype=subtype))

    if event.get("force_stop"):
        events.append(
            AgentEvent(
                kind="lifecycle",
                raw=event,
                subtype="force_stop",
                payload={"reason": event.get("force_stop_reason", "unknown")},
            )
        )

    if event.get("complete") or event.get("result"):
        events.append(AgentEvent(kind="lifecycle", raw=event, subtype="complete"))

    # Text streaming
    if "data" in event:
        events.append(AgentEvent(kind="text", raw=event, payload={"text": event.get("data", "")}))

    # Reasoning signals
    if event.get("reasoning") or "reasoningText" in event:
        events.append(
            AgentEvent(
                kind="reasoning",
                raw=event,
                payload={
                    "text": event.get("reasoningText", ""),
                    "signature": event.get("reasoning_signature"),
                },
            )
        )

    # Tool usage
    tool_use = event.get("current_tool_use")
    if isinstance(tool_use, dict) and tool_use.get("name"):
        events.append(AgentEvent(kind="tool", raw=event, payload=tool_use))

    tool_stream = event.get("tool_stream_event")
    if isinstance(tool_stream, dict):
        events.append(AgentEvent(kind="tool_stream", raw=event, payload=tool_stream))

    # Metrics
    metrics = extract_metrics_from_event(event)
    if metrics is not None:
        events.append(
            AgentEvent(
                kind="metrics",
                raw=event,
                payload=metrics.to_dict(),
                subtype=metrics.stop_reason,
            )
        )

    if not events:
        events.append(AgentEvent(kind="unknown", raw=event))

    return events


def normalize_strands_events(events: Iterable[dict[str, Any]]) -> list[AgentEvent]:
    """Normalize a sequence of Strands events into AgentEvent entries."""
    normalized: list[AgentEvent] = []
    for event in events:
        normalized.extend(normalize_strands_event(event))
    return normalized
