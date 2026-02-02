"""Stream utilities module for agent event processing.

This module provides utilities for handling streaming events from Strands agents:

- OutputAccumulator: Buffers text output and tool events during streaming
- accumulate_output/accumulate_tool_event: Low-level event processing functions
- build_multiagent_prompt: Formats conversation history for swarm/graph modes
- split_messages_for_single_mode: Separates history from current prompt
- create_metadata_event: Creates Phoenix telemetry metadata events

The runtime.py module uses these utilities in execution strategies to
process raw Strands events and build run snapshots.
"""

from agent_toolkit.stream_utils.accumulator import (
    OutputAccumulator,
    accumulate_output,
    accumulate_tool_event,
)
from agent_toolkit.stream_utils.formatters import (
    build_multiagent_prompt,
    extract_prompt_for_log,
    format_tool_input,
    split_messages_for_single_mode,
)
from agent_toolkit.stream_utils.metadata import StreamMetadata, create_metadata_event

__all__ = [
    "OutputAccumulator",
    "StreamMetadata",
    "accumulate_output",
    "accumulate_tool_event",
    "build_multiagent_prompt",
    "create_metadata_event",
    "extract_prompt_for_log",
    "format_tool_input",
    "split_messages_for_single_mode",
]
