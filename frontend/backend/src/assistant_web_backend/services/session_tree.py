"""Session tree persistence helpers for the web backend."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from agent_toolkit.session import SessionManager
from agent_toolkit.session.models import (
    BranchSummaryEntry,
    CompactionEntry,
    CustomEntry,
    CustomMessageEntry,
    LabelEntry,
    ModelChangeEntry,
    SessionEntryBase,
    SessionHeader,
    SessionInfoEntry,
    SessionMessageEntry,
    ThinkingLevelChangeEntry,
)

from assistant_web_backend.models.sessions import (
    SessionEntryView,
    SessionHeaderView,
    SessionTreeResponse,
)

UNKNOWN_PARENT_ID = "Unknown parent entry id"
UNKNOWN_TARGET_ID = "Unknown target entry id"


def _storage_dir() -> Path:
    """Return the base directory for session tree storage."""
    base_dir = Path(os.getenv("WEB_STORAGE_DIR", ".data"))
    return base_dir / "session_tree"


def _session_path(thread_id: str) -> Path:
    """Return the session JSONL path for a thread."""
    return _storage_dir() / f"{thread_id}.jsonl"


def _ensure_manager(thread_id: str) -> SessionManager:
    """Open or create the session tree manager for a thread."""
    path = _session_path(thread_id)
    if path.exists():
        return SessionManager.open(path)
    return SessionManager.create(path)


def append_message_entry(
    thread_id: str,
    message: dict[str, Any],
    *,
    entry_id: str | None = None,
    parent_entry_id: str | None = None,
) -> str:
    """Append a message entry, optionally branching from a parent entry."""
    manager = _ensure_manager(thread_id)
    if parent_entry_id:
        if manager.get_entry(parent_entry_id) is None:
            raise ValueError(UNKNOWN_PARENT_ID)
        manager.branch(parent_entry_id)
    return manager.append_message(message, entry_id=entry_id)


def append_label_entry(thread_id: str, target_id: str, label: str | None) -> str:
    """Append a label change entry for a target session entry."""
    manager = _ensure_manager(thread_id)
    if manager.get_entry(target_id) is None:
        raise ValueError(UNKNOWN_TARGET_ID)
    return manager.append_label_change(target_id, label)


def load_session_tree(thread_id: str) -> SessionTreeResponse:
    """Load a session tree response for a thread."""
    manager = _ensure_manager(thread_id)
    entries = manager.get_entries()
    labels = _collect_labels(entries)

    entry_views: list[SessionEntryView] = []
    children: dict[str, list[str]] = {}
    roots: list[str] = []

    for entry in entries:
        if isinstance(entry, LabelEntry):
            continue
        entry_views.append(_to_entry_view(entry, labels))
        parent_id = entry.parent_id
        if parent_id is None:
            roots.append(entry.id)
        else:
            children.setdefault(parent_id, []).append(entry.id)

    header = _to_header_view(manager.header)
    return SessionTreeResponse(
        sessionId=header.id,
        header=header,
        entries=entry_views,
        roots=roots,
        children=children,
        leafId=manager.get_leaf_id(),
    )


def _collect_labels(entries: list[SessionEntryBase]) -> dict[str, str | None]:
    """Collect label entries keyed by target entry id."""
    labels: dict[str, str | None] = {}
    for entry in entries:
        if isinstance(entry, LabelEntry):
            labels[entry.target_id] = entry.label
    return labels


def _to_header_view(header: SessionHeader) -> SessionHeaderView:
    """Translate a session header into an API view model."""
    return SessionHeaderView(
        id=header.id,
        timestamp=header.timestamp,
        cwd=header.cwd,
        parentSession=header.parent_session,
    )


def _to_entry_view(entry: SessionEntryBase, labels: dict[str, str | None]) -> SessionEntryView:
    """Translate a session entry into an API view model."""
    base = {
        "id": entry.id,
        "parentId": entry.parent_id,
        "type": entry.type,
        "timestamp": entry.timestamp,
        "label": labels.get(entry.id),
    }

    extra: dict[str, Any] = {}
    if isinstance(entry, SessionMessageEntry):
        role, preview = _message_preview(entry.message)
        extra = {"messageRole": role, "messagePreview": preview}
    elif isinstance(entry, CompactionEntry):
        extra = {"summary": entry.summary, "details": entry.details}
    elif isinstance(entry, BranchSummaryEntry):
        extra = {"summary": entry.summary, "details": entry.details, "fromId": entry.from_id}
    elif isinstance(entry, CustomMessageEntry):
        extra = {"customType": entry.custom_type, "details": entry.details}
    elif isinstance(entry, CustomEntry):
        extra = {"customType": entry.custom_type, "details": entry.data}
    elif isinstance(entry, SessionInfoEntry):
        extra = {"summary": entry.name}
    elif isinstance(entry, ModelChangeEntry):
        extra = {"summary": f"{entry.provider}.{entry.model_id}"}
    elif isinstance(entry, ThinkingLevelChangeEntry):
        extra = {"summary": entry.thinking_level}

    return SessionEntryView(**base, **extra)


def _message_preview(message: dict[str, Any]) -> tuple[str | None, str | None]:
    """Return a short role + preview tuple for message content."""
    role = message.get("role") if isinstance(message.get("role"), str) else None
    content = message.get("content", [])
    preview: str | None = None
    if isinstance(content, list):
        for part in content:
            if not isinstance(part, dict):
                continue
            if part.get("type") == "text" and isinstance(part.get("text"), str):
                preview = part.get("text")
                break
    if preview is None:
        return role, None
    preview = " ".join(preview.split())
    if len(preview) > 140:
        preview = preview[:137].rstrip() + "..."
    return role, preview
