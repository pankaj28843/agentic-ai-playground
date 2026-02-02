"""Formatters for streaming content.

Handles prompt extraction, multi-agent prompt building, and tool input formatting.
"""

from __future__ import annotations

import json
from typing import Any


def extract_prompt_for_log(messages: list[dict[str, Any]]) -> str:
    """Extract prompt text from last user message for snapshot logging."""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            for block in msg.get("content", []):
                if "text" in block:
                    return str(block["text"])[:500]
    return ""


def build_multiagent_prompt(messages: list[dict[str, Any]]) -> str:
    """Build a context-rich prompt for multi-agent modes.

    Multi-agent modes (swarm/graph) only accept string prompts.
    This serializes the conversation history into a single prompt string
    so the agents have context of the conversation.
    """
    if not messages:
        return ""

    parts: list[str] = []

    # Include conversation history (limit to last 10 messages to avoid bloat)
    history_msgs = messages[:-1][-10:] if len(messages) > 1 else []
    if history_msgs:
        parts.append("<conversation_history>")
        for msg in history_msgs:
            role = msg.get("role", "unknown")
            for block in msg.get("content", []):
                if "text" in block:
                    text = str(block["text"])[:1000]  # Truncate long messages
                    parts.append(f"[{role}]: {text}")
        parts.append("</conversation_history>\n")

    # Add the current user message
    for msg in reversed(messages):
        if msg.get("role") == "user":
            for block in msg.get("content", []):
                if "text" in block:
                    parts.append(f"Current request: {block['text']}")
                    break
            break

    return "\n".join(parts)


def format_tool_input(payload: Any) -> str:
    """Format tool input payload for display/logging."""
    if isinstance(payload, str):
        return payload[:200]
    try:
        return json.dumps(payload, ensure_ascii=True)[:200]
    except TypeError:
        return str(payload)[:200]


def split_messages_for_single_mode(
    messages: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Split messages into last user prompt and history.

    Single agent mode requires separating the current prompt from history
    so history can be injected into agent.messages while the prompt is
    passed to the agent invocation.

    Args:
        messages: Full conversation history in Strands message format.

    Returns:
        Tuple of (last_user_prompt, history_messages)
    """
    last_user_prompt: str = ""
    history_messages: list[dict[str, Any]] = []

    for i, msg in enumerate(messages):
        if msg.get("role") == "user":
            is_last_user = all(m.get("role") != "user" for m in messages[i + 1 :])
            if is_last_user:
                for block in msg.get("content", []):
                    if "text" in block:
                        last_user_prompt = str(block["text"])
                        break
            else:
                history_messages.append(msg)
        else:
            history_messages.append(msg)

    return last_user_prompt, history_messages
