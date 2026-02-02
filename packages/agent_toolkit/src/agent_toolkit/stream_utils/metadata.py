"""Metadata handling for streaming responses.

Provides utilities for creating and managing stream metadata events
containing Phoenix trace information.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class StreamMetadata:
    """Metadata captured during streaming for Phoenix integration."""

    trace_id: str | None = None
    session_id: str | None = None
    metrics: dict[str, Any] | None = None

    def to_event(self) -> dict[str, Any] | None:
        """Convert to a stream metadata event dict."""
        if not self.trace_id:
            return None
        return create_metadata_event(self.trace_id, self.session_id)


def create_metadata_event(
    trace_id: str | None,
    session_id: str | None = None,
) -> dict[str, Any]:
    """Create a stream metadata event with Phoenix trace info.

    Args:
        trace_id: Phoenix trace ID
        session_id: Phoenix session ID

    Returns:
        Event dict suitable for yielding in a stream
    """
    event: dict[str, Any] = {"type": "stream_metadata"}
    if trace_id:
        event["phoenix_trace_id"] = trace_id
    if session_id:
        event["phoenix_session_id"] = session_id
    return event
