"""Utilities for compaction and branch summarization."""

from __future__ import annotations

from typing import Any

from agent_toolkit.compaction.models import FileOps


def estimate_tokens(text: str) -> int:
    """Rough token estimate using 4 chars per token heuristic."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def _extract_text_from_message(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = [
            str(item.get("text", ""))
            for item in content
            if isinstance(item, dict) and (item.get("type") == "text" or "text" in item)
        ]
        return "\n".join(chunks)
    return ""


def estimate_message_tokens(message: dict[str, Any]) -> int:
    """Estimate token usage for a single message."""
    return estimate_tokens(_extract_text_from_message(message))


def extract_file_ops(messages: list[dict[str, Any]]) -> FileOps:
    """Extract read/write file paths referenced by tool calls."""
    read_files: list[str] = []
    modified_files: list[str] = []

    for message in messages:
        _collect_paths_from_content(message.get("content", []), read_files, modified_files)
        _collect_paths_from_tool_message(message, read_files, modified_files)

    return FileOps(read_files=sorted(set(read_files)), modified_files=sorted(set(modified_files)))


def _record_path(target: list[str], path: Any) -> None:
    if not path:
        return
    if isinstance(path, str):
        target.append(path)
    elif isinstance(path, list):
        target.extend(item for item in path if isinstance(item, str))


def _record_tool_path(
    tool_name: str | None, args: Any, read_files: list[str], modified_files: list[str]
) -> None:
    if not tool_name:
        return
    path = args.get("path") if isinstance(args, dict) else None
    if "read" in tool_name:
        _record_path(read_files, path)
    if any(key in tool_name for key in ("write", "edit", "patch")):
        _record_path(modified_files, path)


def _collect_paths_from_content(
    content: Any, read_files: list[str], modified_files: list[str]
) -> None:
    if not isinstance(content, list):
        return
    for part in content:
        if not isinstance(part, dict):
            continue
        part_type = part.get("type")
        tool_name = part.get("toolName") or part.get("name")
        args = part.get("args") or part.get("input") or {}
        if part_type in ("tool-call", "toolUse") or tool_name:
            _record_tool_path(tool_name or "", args, read_files, modified_files)


def _collect_paths_from_tool_message(
    message: dict[str, Any], read_files: list[str], modified_files: list[str]
) -> None:
    if message.get("role") not in ("tool", "toolResult"):
        return
    tool_name = message.get("toolName")
    if isinstance(tool_name, str):
        _record_tool_path(tool_name, message.get("args", {}), read_files, modified_files)


def format_structured_summary(
    goal: str,
    constraints: list[str],
    done: list[str],
    in_progress: list[str],
    blocked: list[str],
    decisions: list[str],
    next_steps: list[str],
    file_ops: FileOps,
) -> str:
    """Format a structured summary for compaction output."""
    lines: list[str] = ["## Goal", goal or "(not specified)", "", "## Constraints & Preferences"]
    lines.extend(f"- {item}" for item in constraints or ["(none)"])
    lines.append("")
    lines.append("## Progress")
    lines.append("### Done")
    lines.extend(f"- [x] {item}" for item in done or ["(none)"])
    lines.append("### In Progress")
    lines.extend(f"- [ ] {item}" for item in in_progress or ["(none)"])
    lines.append("### Blocked")
    lines.extend(f"- {item}" for item in blocked or ["(none)"])
    lines.append("")
    lines.append("## Key Decisions")
    lines.extend(f"- {item}" for item in decisions or ["(none)"])
    lines.append("")
    lines.append("## Next Steps")
    if next_steps:
        lines.extend(f"{idx}. {item}" for idx, item in enumerate(next_steps, start=1))
    else:
        lines.append("1. (none)")
    lines.append("")
    lines.append("## Critical Context")
    lines.append("(none)")
    lines.append("")
    lines.append("<read-files>")
    lines.extend(file_ops.read_files)
    lines.append("</read-files>")
    lines.append("")
    lines.append("<modified-files>")
    lines.extend(file_ops.modified_files)
    lines.append("</modified-files>")
    return "\n".join(lines)
