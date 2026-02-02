"""Normalized streaming chunk abstraction.

This module provides a higher-level abstraction over raw Strands streaming events.
StreamChunk normalizes the various event types into a consistent format with
explicit lifecycle states (cycle_start, complete, force_stop, etc.).

Usage:
    The runtime.py module uses raw Strands events directly with OutputAccumulator.
    This module is available for consumers who want a more structured streaming
    interface with typed chunk objects.

Note:
    This is a public API exported from agent_toolkit for external consumers.
    The test suite validates the normalization behavior.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_toolkit.metrics import extract_metrics_from_event


@dataclass(frozen=True)
class StreamChunk:
    """Normalized streaming chunk from an agent.

    Provides a consistent interface over raw Strands streaming events.

    Kinds:
    - "text": Text generation chunk
    - "tool": Tool invocation info
    - "cycle_start": Agent loop cycle beginning
    - "complete": Run completed normally
    - "force_stop": Run force-stopped
    - "error": Error occurred
    - "metrics": Final metrics available

    Example:
        async for chunk in stream_agent(agent, "hello"):
            if chunk.kind == "text":
                print(chunk.data)
    """

    kind: str
    data: str | dict
    stop_reason: str | None = None
    metrics: dict | None = None


async def stream_agent(agent, prompt: str):
    """Yield normalized streaming chunks from a Strands agent.

    Normalizes the raw Strands streaming events into StreamChunk objects
    with consistent structure and lifecycle events.

    Args:
        agent: A Strands Agent instance
        prompt: The prompt to send to the agent

    Yields:
        StreamChunk instances for each event type
    """
    async for event in agent.stream_async(prompt):
        # Lifecycle events
        if event.get("start_event_loop"):
            yield StreamChunk(kind="cycle_start", data={})

        # Text content
        if "data" in event:
            yield StreamChunk(kind="text", data=event["data"])

        # Tool usage
        if "current_tool_use" in event:
            tool_use = event["current_tool_use"] or {}
            if tool_use.get("name"):
                yield StreamChunk(kind="tool", data=tool_use)

        # Force stop with reason
        if event.get("force_stop"):
            reason = event.get("force_stop_reason", "unknown")
            yield StreamChunk(kind="force_stop", data={}, stop_reason=reason)

        # Normal completion
        if event.get("complete"):
            yield StreamChunk(kind="complete", data={}, stop_reason="end_turn")

        # Final result with metrics
        agent_metrics = extract_metrics_from_event(event)
        if agent_metrics is not None:
            yield StreamChunk(
                kind="metrics",
                data={},
                stop_reason=agent_metrics.stop_reason,
                metrics=agent_metrics.to_dict(),
            )
