"""Models for compaction and branch summarization."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class FileOps:
    """File operations tracked during compaction."""

    read_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CompactionSettings:
    """Token budgeting settings for compaction."""

    reserve_tokens: int = 16384
    keep_recent_tokens: int = 20000


@dataclass(frozen=True)
class CompactionPreparation:
    """Computed data needed to run compaction."""

    messages_to_summarize: list[dict[str, Any]]
    kept_messages: list[dict[str, Any]]
    first_kept_index: int
    tokens_before: int
    file_ops: FileOps


@dataclass(frozen=True)
class CompactionResult:
    """Summary output from compaction."""

    summary: str
    first_kept_index: int
    tokens_before: int
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class BranchSummaryPreparation:
    """Computed data needed to summarize a branch."""

    entries_to_summarize: list[dict[str, Any]]
    tokens_before: int
    file_ops: FileOps


@dataclass(frozen=True)
class BranchSummaryResult:
    """Summary output for a session branch."""

    summary: str
    details: dict[str, Any] | None = None


@dataclass(frozen=True)
class CompactionOverride:
    """Override payload for compaction hook results."""

    summary: str
    first_kept_index: int
    tokens_before: int
    details: dict[str, Any] | None = None


class CompactionHook(Protocol):
    """Hook interface for compaction customization."""

    def before_compact(self, preparation: CompactionPreparation) -> CompactionOverride | None:
        """Optionally return a compaction override."""
        ...


Summarizer = Callable[[list[dict[str, Any]]], str]
