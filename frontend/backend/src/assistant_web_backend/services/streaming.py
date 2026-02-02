"""Streaming service for agent responses.

Handles accumulation and processing of streaming events from the agent runtime.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from assistant_web_backend.models.messages import ContentPart, ToolCallStatus


class StreamState:
    """Accumulates rich content during streaming."""

    def __init__(self) -> None:
        self.text_buffer: list[str] = []
        self.tool_calls: dict[str, ContentPart] = {}
        self.reasoning_parts: list[ContentPart] = []
        self.agent_events: list[ContentPart] = []
        self.start_time: float = datetime.now(UTC).timestamp()
        self._seen_thinking_hashes: set[str] = set()
        self._active_agents: dict[
            str, ContentPart
        ] = {}  # Track agents that started but not stopped
        self._current_agent: str | None = None  # Currently executing agent in multi-agent mode

    def _relative_timestamp(self) -> str:
        """Get timestamp relative to stream start in ISO format with ms precision."""
        now = datetime.now(UTC)
        return now.isoformat()

    def _elapsed_ms(self) -> float:
        """Get elapsed milliseconds since stream start."""
        return (datetime.now(UTC).timestamp() - self.start_time) * 1000

    def _extract_thinking_blocks(self, text: str) -> None:
        """Extract <thinking> blocks from text and add them as reasoning parts."""
        pattern = r"<thinking>([\s\S]*?)</thinking>"
        for match in re.finditer(pattern, text):
            content = match.group(1).strip()
            if content:
                content_hash = hashlib.sha256(content.encode()).hexdigest()
                if content_hash not in self._seen_thinking_hashes:
                    self._seen_thinking_hashes.add(content_hash)
                    self.reasoning_parts.append(
                        ContentPart(
                            type="reasoning",
                            text=content,
                            timestamp=self._relative_timestamp(),
                        )
                    )

    def build_content(self) -> list[ContentPart]:
        """Build content array from accumulated state, sorted by timestamp."""
        full_text = "".join(self.text_buffer)
        self._extract_thinking_blocks(full_text)

        parts: list[ContentPart] = []
        if self.text_buffer:
            parts.append(ContentPart(type="text", text=full_text))

        timestamped_parts: list[ContentPart] = []
        timestamped_parts.extend(self.reasoning_parts)
        timestamped_parts.extend(self.tool_calls.values())
        timestamped_parts.extend(self.agent_events)
        timestamped_parts.sort(key=lambda p: p.timestamp or "")

        parts.extend(timestamped_parts)
        return parts

    def get_text_content(self) -> str:
        """Get accumulated text content without thinking blocks."""
        full_text = "".join(self.text_buffer)
        # Strip thinking blocks for evaluation
        clean_text = re.sub(r"<thinking>[\s\S]*?</thinking>", "", full_text)
        return clean_text.strip()

    def handle_event(self, event_data: dict[str, Any]) -> bool:
        """Process an event and return True if state changed."""
        changed = False

        # Handle multi-agent orchestration events first
        event_type = event_data.get("type")
        if event_type in (
            "multiagent_node_start",
            "multiagent_node_stop",
            "multiagent_handoff",
            "multiagent_node_stream",
        ):
            changed = self._handle_multiagent_event(event_data) or changed
            # For node_stream, also process the inner event
            if event_type == "multiagent_node_stream":
                inner_event = event_data.get("event", {})
                if isinstance(inner_event, dict):
                    changed = self._handle_inner_event(inner_event) or changed
            return changed

        changed = self._handle_nested_event(event_data) or changed
        changed = self._handle_delta_tool_use(event_data) or changed
        changed = self._handle_text_data(event_data) or changed

        tool_use = event_data.get("current_tool_use")
        if isinstance(tool_use, dict):
            changed = self._handle_tool_start(tool_use) or changed

        tool_result = event_data.get("tool_result")
        if tool_result is None and event_data.get("type") == "tool_result":
            tool_result = event_data
        if tool_result is None:
            tool_result = event_data.get("tool_output")
        if tool_result is not None:
            changed = self._handle_tool_result(event_data, tool_result) or changed

        message = event_data.get("message")
        if isinstance(message, dict) and message.get("role") == "user":
            content = message.get("content", [])
            for item in content:
                if isinstance(item, dict) and "toolResult" in item:
                    tr = item["toolResult"]
                    changed = (
                        self._handle_tool_result({"toolUseId": tr.get("toolUseId")}, tr) or changed
                    )

        return self._handle_reasoning_event(event_data) or changed

    def _handle_inner_event(self, event_data: dict[str, Any]) -> bool:
        """Process inner event from multiagent_node_stream."""
        changed = False
        changed = self._handle_nested_event(event_data) or changed
        changed = self._handle_delta_tool_use(event_data) or changed
        changed = self._handle_text_data(event_data) or changed

        tool_use = event_data.get("current_tool_use")
        if isinstance(tool_use, dict):
            changed = self._handle_tool_start(tool_use) or changed

        tool_result = event_data.get("tool_result") or event_data.get("tool_output")
        if tool_result is not None:
            changed = self._handle_tool_result(event_data, tool_result) or changed

        return self._handle_reasoning_event(event_data) or changed

    def _handle_multiagent_event(self, event_data: dict[str, Any]) -> bool:
        """Handle multi-agent orchestration events (node_start, node_stop, handoff)."""
        event_type = event_data.get("type", "")
        node_id = event_data.get("node_id", "")
        timestamp = self._relative_timestamp()

        if event_type == "multiagent_node_start":
            # Agent/node is starting execution - track as current agent
            self._current_agent = node_id
            agent_event = ContentPart(
                type="agent-event",
                agent_name=node_id,
                event_type="start",
                timestamp=timestamp,
            )
            self._active_agents[node_id] = agent_event
            self.agent_events.append(agent_event)
            return True

        if event_type == "multiagent_node_stop":
            # Agent/node completed - update existing or create new
            if node_id in self._active_agents:
                # Update existing agent event
                existing = self._active_agents.pop(node_id)
                existing.event_type = "complete"
            else:
                # No start event found, create a complete event
                self.agent_events.append(
                    ContentPart(
                        type="agent-event",
                        agent_name=node_id,
                        event_type="complete",
                        timestamp=timestamp,
                    )
                )
            # Clear current agent when it stops
            if self._current_agent == node_id:
                self._current_agent = None
            return True

        if event_type == "multiagent_handoff":
            # Handoff between agents in swarm - extract message/reason if available
            from_nodes = event_data.get("from_node_ids", [])
            to_nodes = event_data.get("to_node_ids", [])
            # The handoff message may be in different locations depending on SDK version
            handoff_message = (
                event_data.get("message")
                or event_data.get("handoff_message")
                or event_data.get("context", {}).get("message")
            )
            self.agent_events.append(
                ContentPart(
                    type="agent-event",
                    event_type="handoff",
                    from_agents=from_nodes,
                    to_agents=to_nodes,
                    handoff_message=handoff_message,
                    timestamp=timestamp,
                )
            )
            return True

        return False

    def _handle_nested_event(self, event_data: dict[str, Any]) -> bool:
        """Handle nested 'event' structure from Strands SDK."""
        nested_event = event_data.get("event")
        if not isinstance(nested_event, dict):
            return False
        changed = False
        if nested_event.get("current_tool_use"):
            tool_use = nested_event.get("current_tool_use")
            changed = self._handle_tool_start(tool_use) or changed
        if nested_event.get("tool_result") or nested_event.get("tool_output"):
            result = nested_event.get("tool_result") or nested_event.get("tool_output")
            changed = self._handle_tool_result(nested_event, result) or changed
        return changed

    def _handle_delta_tool_use(self, event_data: dict[str, Any]) -> bool:
        """Handle tool use info from delta (Strands/Bedrock format)."""
        delta = event_data.get("delta")
        if not isinstance(delta, dict):
            return False
        tool_use_delta = delta.get("toolUse")
        if not tool_use_delta or not tool_use_delta.get("name"):
            return False
        return self._handle_tool_start(
            {
                "toolUseId": tool_use_delta.get("toolUseId"),
                "name": tool_use_delta.get("name"),
                "input": tool_use_delta.get("input", {}),
            }
        )

    def _handle_text_data(self, event_data: dict[str, Any]) -> bool:
        """Handle text data from streaming event."""
        text = event_data.get("data")
        if not isinstance(text, str):
            return False
        self.text_buffer.append(text)
        full_text = "".join(self.text_buffer)
        self._extract_thinking_blocks(full_text)
        return True

    def _handle_reasoning_event(self, event_data: dict[str, Any]) -> bool:
        """Handle reasoning from SDK (if separate from <thinking> tags)."""
        if not event_data.get("reasoning"):
            return False
        reasoning_text = event_data.get("reasoningText", "")
        if not reasoning_text:
            return False
        content_hash = hashlib.sha256(reasoning_text.encode()).hexdigest()
        if content_hash in self._seen_thinking_hashes:
            return False
        self._seen_thinking_hashes.add(content_hash)
        self.reasoning_parts.append(
            ContentPart(
                type="reasoning",
                text=reasoning_text,
                timestamp=self._relative_timestamp(),
            )
        )
        return True

    def _handle_tool_start(self, tool_use: dict[str, Any]) -> bool:
        tool_id = tool_use.get("toolUseId") or str(uuid4())
        tool_name = tool_use.get("name", "unknown")
        tool_input = tool_use.get("input", {})
        args_dict = tool_input if isinstance(tool_input, dict) else {}
        try:
            args_text = json.dumps(tool_input) if tool_input else None
        except (TypeError, ValueError):
            args_text = str(tool_input) if tool_input else None
        self.tool_calls[tool_id] = ContentPart(
            type="tool-call",
            tool_name=tool_name,
            tool_call_id=tool_id,
            args=args_dict,
            args_text=args_text,
            status=ToolCallStatus(type="running"),
            timestamp=self._relative_timestamp(),
            calling_agent=self._current_agent,  # Track which agent made this call
        )
        return True

    def _serialize_tool_result(self, result: Any) -> str | None:
        """Serialize tool result to string for safe JSON encoding."""
        if result is None:
            return None
        if isinstance(result, str):
            return result
        if isinstance(result, (dict, list)):
            try:
                return json.dumps(result, default=str)
            except (TypeError, ValueError):
                return repr(result)
        return str(result)

    def _handle_tool_result(self, event_data: dict[str, Any], result: Any) -> bool:
        result_tool_id = event_data.get("toolUseId")
        is_error = event_data.get("isError", False)

        if isinstance(result, dict):
            if not result_tool_id:
                result_tool_id = result.get("toolUseId")
            is_error = result.get("status") == "error"
            content = result.get("content")
            if content is not None:
                result = content

        serialized_result = self._serialize_tool_result(result)

        if result_tool_id and result_tool_id in self.tool_calls:
            tool = self.tool_calls[result_tool_id]
            tool.result = serialized_result
            tool.status = ToolCallStatus(type="complete")
            tool.is_error = is_error
            return True

        if self.tool_calls:
            last_tool = list(self.tool_calls.values())[-1]
            last_tool.result = serialized_result
            last_tool.status = ToolCallStatus(type="complete")
            last_tool.is_error = is_error
            return True

        return False
