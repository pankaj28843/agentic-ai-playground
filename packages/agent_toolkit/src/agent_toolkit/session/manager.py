"""Session manager for tree-based JSONL persistence."""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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

SESSION_FILE_EMPTY = "Session file is empty"
UNKNOWN_ENTRY_ID = "Unknown entry id"
DUPLICATE_ENTRY_ID = "Duplicate entry id"

ENTRY_TYPE_MAP: dict[str, type[SessionEntryBase]] = {
    "message": SessionMessageEntry,
    "compaction": CompactionEntry,
    "branch_summary": BranchSummaryEntry,
    "custom": CustomEntry,
    "custom_message": CustomMessageEntry,
    "label": LabelEntry,
    "session_info": SessionInfoEntry,
    "model_change": ModelChangeEntry,
    "thinking_level_change": ThinkingLevelChangeEntry,
}


def _utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    """Generate a short random identifier."""
    return secrets.token_hex(4)


def _drop_none(data: dict[str, Any], keep: set[str] | None = None) -> dict[str, Any]:
    """Drop None values from a dict while keeping specified keys."""
    keep = keep or set()
    return {k: v for k, v in data.items() if v is not None or k in keep}


def _serialize_header(header: SessionHeader) -> dict[str, Any]:
    """Serialize a header into JSON-ready payload."""
    data = header.to_dict()
    if "parent_session" in data:
        data["parentSession"] = data.pop("parent_session")
    return data


def _serialize_entry(entry: SessionEntryBase) -> dict[str, Any]:
    """Serialize an entry into JSON-ready payload."""
    data = asdict(entry)
    # Rename common fields to camelCase
    if "parent_id" in data:
        data["parentId"] = data.pop("parent_id")
    if "custom_type" in data:
        data["customType"] = data.pop("custom_type")
    if "from_id" in data:
        data["fromId"] = data.pop("from_id")
    if "first_kept_entry_id" in data:
        data["firstKeptEntryId"] = data.pop("first_kept_entry_id")
    if "tokens_before" in data:
        data["tokensBefore"] = data.pop("tokens_before")
    if "model_id" in data:
        data["modelId"] = data.pop("model_id")
    if "thinking_level" in data:
        data["thinkingLevel"] = data.pop("thinking_level")
    return _drop_none(data, keep={"parentId"})


def _deserialize_entry(raw: dict[str, Any]) -> SessionEntryBase:
    """Deserialize a JSON payload into a session entry."""
    # Map camelCase back to snake_case
    normalized = dict(raw)
    if "parentId" in normalized:
        normalized["parent_id"] = normalized.pop("parentId")
    if "parent_id" not in normalized:
        normalized["parent_id"] = None
    if "customType" in normalized:
        normalized["custom_type"] = normalized.pop("customType")
    if "fromId" in normalized:
        normalized["from_id"] = normalized.pop("fromId")
    if "firstKeptEntryId" in normalized:
        normalized["first_kept_entry_id"] = normalized.pop("firstKeptEntryId")
    if "tokensBefore" in normalized:
        normalized["tokens_before"] = normalized.pop("tokensBefore")
    if "modelId" in normalized:
        normalized["model_id"] = normalized.pop("modelId")
    if "thinkingLevel" in normalized:
        normalized["thinking_level"] = normalized.pop("thinkingLevel")

    entry_type = normalized.get("type")
    entry_cls = ENTRY_TYPE_MAP.get(entry_type, SessionEntryBase)
    return entry_cls(**normalized)


def _deserialize_header(raw: dict[str, Any]) -> SessionHeader:
    """Deserialize a JSON payload into a session header."""
    normalized = dict(raw)
    if "parentSession" in normalized:
        normalized["parent_session"] = normalized.pop("parentSession")
    return SessionHeader(**normalized)


class SessionManager:
    """Manage JSONL session files with tree-based branching."""

    def __init__(self, path: Path, header: SessionHeader) -> None:
        self._path = path
        self._header = header
        self._entries: dict[str, SessionEntryBase] = {}
        self._order: list[str] = []
        self._leaf_id: str | None = None

    @classmethod
    def create(cls, path: str | Path, cwd: str | None = None, parent_session: str | None = None):
        """Create a new session file and manager."""
        file_path = Path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        header = SessionHeader(
            type="session",
            version=3,
            id=_new_id(),
            timestamp=_utc_timestamp(),
            cwd=cwd,
            parent_session=parent_session,
        )
        file_path.write_text(json.dumps(_serialize_header(header)) + "\n", encoding="utf-8")
        return cls(file_path, header)

    @classmethod
    def open(cls, path: str | Path) -> SessionManager:
        """Open an existing session file."""
        file_path = Path(path)
        lines = file_path.read_text(encoding="utf-8").splitlines()
        if not lines:
            raise ValueError(SESSION_FILE_EMPTY)
        header_raw = json.loads(lines[0])
        header = _deserialize_header(header_raw)
        manager = cls(file_path, header)
        for line in lines[1:]:
            if not line.strip():
                continue
            raw = json.loads(line)
            entry = _deserialize_entry(raw)
            manager._entries[entry.id] = entry
            manager._order.append(entry.id)
            manager._leaf_id = entry.id
        return manager

    @property
    def header(self) -> SessionHeader:
        """Return the session header."""
        return self._header

    @property
    def path(self) -> Path:
        """Return the backing JSONL path."""
        return self._path

    def get_entries(self) -> list[SessionEntryBase]:
        """Return entries in insertion order."""
        return [self._entries[entry_id] for entry_id in self._order]

    def get_entry(self, entry_id: str) -> SessionEntryBase | None:
        """Return an entry by id if present."""
        return self._entries.get(entry_id)

    def get_leaf_id(self) -> str | None:
        """Return the current leaf entry id."""
        return self._leaf_id

    def get_tree(self) -> dict[str | None, list[str]]:
        """Return a parent->children mapping for the session."""
        tree: dict[str | None, list[str]] = {}
        for entry_id in self._order:
            entry = self._entries[entry_id]
            tree.setdefault(entry.parent_id, []).append(entry_id)
        return tree

    def get_children(self, parent_id: str | None) -> list[SessionEntryBase]:
        """Return child entries for a parent entry id."""
        tree = self.get_tree()
        return [self._entries[child_id] for child_id in tree.get(parent_id, [])]

    def get_branch(self, from_id: str | None = None) -> list[SessionEntryBase]:
        """Return a branch from the specified entry up to the root."""
        start_id = from_id or self._leaf_id
        if start_id is None:
            return []
        branch: list[SessionEntryBase] = []
        current_id = start_id
        while current_id is not None:
            entry = self._entries.get(current_id)
            if entry is None:
                break
            branch.append(entry)
            current_id = entry.parent_id
        return branch

    def branch(self, entry_id: str) -> None:
        """Set the leaf pointer to an existing entry id."""
        if entry_id not in self._entries:
            raise ValueError(UNKNOWN_ENTRY_ID)
        self._leaf_id = entry_id

    def append_message(
        self,
        message: dict[str, Any],
        *,
        entry_id: str | None = None,
        parent_id: str | None = None,
    ) -> str:
        """Append a message entry and return its id."""
        parent = parent_id if parent_id is not None else self._leaf_id
        new_id = entry_id or _new_id()
        if new_id in self._entries:
            raise ValueError(DUPLICATE_ENTRY_ID)
        entry = SessionMessageEntry(
            type="message",
            id=new_id,
            parent_id=parent,
            timestamp=_utc_timestamp(),
            message=message,
        )
        return self._append_entry(entry)

    def append_compaction(
        self,
        summary: str,
        first_kept_entry_id: str,
        tokens_before: int,
        details: dict[str, Any] | None = None,
        from_hook: bool | None = None,
    ) -> str:
        """Append a compaction summary entry."""
        entry = CompactionEntry(
            type="compaction",
            id=_new_id(),
            parent_id=self._leaf_id,
            timestamp=_utc_timestamp(),
            summary=summary,
            first_kept_entry_id=first_kept_entry_id,
            tokens_before=tokens_before,
            details=details,
            from_hook=from_hook,
        )
        return self._append_entry(entry)

    def append_branch_summary(
        self,
        summary: str,
        from_id: str,
        details: dict[str, Any] | None = None,
        from_hook: bool | None = None,
    ) -> str:
        """Append a branch summary entry."""
        entry = BranchSummaryEntry(
            type="branch_summary",
            id=_new_id(),
            parent_id=self._leaf_id,
            timestamp=_utc_timestamp(),
            summary=summary,
            from_id=from_id,
            details=details,
            from_hook=from_hook,
        )
        return self._append_entry(entry)

    def append_custom_entry(self, custom_type: str, data: dict[str, Any] | None = None) -> str:
        """Append a custom entry."""
        entry = CustomEntry(
            type="custom",
            id=_new_id(),
            parent_id=self._leaf_id,
            timestamp=_utc_timestamp(),
            custom_type=custom_type,
            data=data,
        )
        return self._append_entry(entry)

    def append_custom_message(
        self,
        custom_type: str,
        content: Any,
        display: bool,
        details: dict[str, Any] | None = None,
    ) -> str:
        """Append a custom message entry."""
        entry = CustomMessageEntry(
            type="custom_message",
            id=_new_id(),
            parent_id=self._leaf_id,
            timestamp=_utc_timestamp(),
            custom_type=custom_type,
            content=content,
            display=display,
            details=details,
        )
        return self._append_entry(entry)

    def append_label_change(self, target_id: str, label: str | None) -> str:
        """Append a label change entry."""
        entry = LabelEntry(
            type="label",
            id=_new_id(),
            parent_id=self._leaf_id,
            timestamp=_utc_timestamp(),
            target_id=target_id,
            label=label,
        )
        return self._append_entry(entry)

    def append_session_info(self, name: str | None) -> str:
        """Append session info metadata."""
        entry = SessionInfoEntry(
            type="session_info",
            id=_new_id(),
            parent_id=self._leaf_id,
            timestamp=_utc_timestamp(),
            name=name,
        )
        return self._append_entry(entry)

    def append_model_change(self, provider: str, model_id: str) -> str:
        """Append a model change entry."""
        entry = ModelChangeEntry(
            type="model_change",
            id=_new_id(),
            parent_id=self._leaf_id,
            timestamp=_utc_timestamp(),
            provider=provider,
            model_id=model_id,
        )
        return self._append_entry(entry)

    def append_thinking_level_change(self, thinking_level: str) -> str:
        """Append a thinking level change entry."""
        entry = ThinkingLevelChangeEntry(
            type="thinking_level_change",
            id=_new_id(),
            parent_id=self._leaf_id,
            timestamp=_utc_timestamp(),
            thinking_level=thinking_level,
        )
        return self._append_entry(entry)

    def _append_entry(self, entry: SessionEntryBase) -> str:
        if entry.id in self._entries:
            raise ValueError(DUPLICATE_ENTRY_ID)
        self._entries[entry.id] = entry
        self._order.append(entry.id)
        self._leaf_id = entry.id
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(_serialize_entry(entry)) + "\n")
        return entry.id
