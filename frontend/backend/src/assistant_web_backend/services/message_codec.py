"""Message conversion helpers for Strands runtime."""

from __future__ import annotations

from typing import Any


def convert_to_strands_messages(
    messages: list,
    *,
    compact_tools: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convert assistant-ui messages to Strands SDK message format."""
    strands_messages: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "message_count": 0,
        "tool_calls_stripped": 0,
        "tool_results_kept": 0,
        "tool_calls_by_name": {},
    }

    for msg in messages:
        if msg.role not in ("user", "assistant"):
            continue

        content_blocks: list[dict[str, Any]] = []
        for part in msg.content:
            part_type = part.get("type")

            if part_type == "text":
                text = part.get("text", "")
                if text:
                    content_blocks.append({"text": text})
            elif part_type == "tool-call":
                block = _convert_tool_call_part(part, compact_tools, stats)
                if block:
                    content_blocks.append(block)
            elif part_type == "tool-result":
                content_blocks.append(_convert_tool_result_part(part, compact_tools, stats))

        if content_blocks:
            strands_messages.append({"role": msg.role, "content": content_blocks})
            stats["message_count"] += 1

    return strands_messages, stats


def _convert_tool_call_part(
    part: dict[str, Any], compact: bool, stats: dict[str, Any]
) -> dict[str, Any] | None:
    """Convert a tool-call content part to Strands format."""
    tool_name = part.get("toolName", "")
    stats["tool_calls_by_name"][tool_name] = stats["tool_calls_by_name"].get(tool_name, 0) + 1

    if compact:
        stats["tool_calls_stripped"] += 1
        return None
    return {
        "toolUse": {
            "toolUseId": part.get("toolCallId", ""),
            "name": tool_name,
            "input": part.get("args", {}),
        }
    }


def _convert_tool_result_part(
    part: dict[str, Any], compact: bool, stats: dict[str, Any]
) -> dict[str, Any]:
    """Convert a tool-result content part to Strands format."""
    result_content = part.get("result")
    stats["tool_results_kept"] += 1

    if compact:
        preview = str(result_content)[:200] if result_content else "No result"
        if len(str(result_content)) > 200:
            preview += "..."
        return {"text": f"[Tool result: {preview}]"}
    return {
        "toolResult": {
            "toolUseId": part.get("toolCallId", ""),
            "content": [{"text": str(result_content)}] if result_content else [],
            "status": "error" if part.get("isError") else "success",
        }
    }
