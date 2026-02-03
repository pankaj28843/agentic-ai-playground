"""Session models for tree-based JSONL persistence."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

EntryType = Literal[
    "session",
    "message",
    "compaction",
    "branch_summary",
    "custom",
    "custom_message",
    "label",
    "session_info",
    "model_change",
    "thinking_level_change",
]


@dataclass(frozen=True)
class SessionHeader:
    """Header entry for a session JSONL file."""

    type: Literal["session"]
    version: int
    id: str
    timestamp: str
    cwd: str | None = None
    parent_session: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize the header to a JSON-compatible dict."""
        data = asdict(self)
        if data.get("cwd") is None:
            data.pop("cwd")
        if data.get("parent_session") is None:
            data.pop("parent_session")
        return data


@dataclass(frozen=True)
class SessionEntryBase:
    """Base class for session entries in the tree."""

    type: EntryType
    id: str
    parent_id: str | None
    timestamp: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entry to a JSON-compatible dict."""
        return asdict(self)


@dataclass(frozen=True)
class SessionMessageEntry(SessionEntryBase):
    """Session entry that stores a chat message."""

    message: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class CompactionEntry(SessionEntryBase):
    """Session entry that stores a compaction summary."""

    summary: str
    first_kept_entry_id: str
    tokens_before: int
    details: dict[str, Any] | None = None
    from_hook: bool | None = None


@dataclass(frozen=True)
class BranchSummaryEntry(SessionEntryBase):
    """Session entry that stores a branch summary."""

    summary: str
    from_id: str
    details: dict[str, Any] | None = None
    from_hook: bool | None = None


@dataclass(frozen=True)
class CustomEntry(SessionEntryBase):
    """Session entry for arbitrary custom payloads."""

    custom_type: str
    data: dict[str, Any] | None = None


@dataclass(frozen=True)
class CustomMessageEntry(SessionEntryBase):
    """Session entry for UI-only message payloads."""

    custom_type: str
    content: Any
    display: bool
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class LabelEntry(SessionEntryBase):
    """Session entry that assigns a label to another entry."""

    target_id: str
    label: str | None


@dataclass(frozen=True)
class SessionInfoEntry(SessionEntryBase):
    """Session entry for storing human-friendly metadata."""

    name: str | None = None


@dataclass(frozen=True)
class ModelChangeEntry(SessionEntryBase):
    """Session entry for a model change event."""

    provider: str
    model_id: str


@dataclass(frozen=True)
class ThinkingLevelChangeEntry(SessionEntryBase):
    """Session entry for a thinking level change."""

    thinking_level: str
