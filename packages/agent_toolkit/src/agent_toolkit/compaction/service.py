"""Compaction policy service for stream context windows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agent_toolkit.compaction.compaction import prepare_compaction
from agent_toolkit.compaction.models import CompactionSettings
from agent_toolkit.compaction.utils import estimate_message_tokens

if TYPE_CHECKING:
    from agent_toolkit.models.settings import Settings


@dataclass(frozen=True)
class StreamCompactionDecision:
    """Result of applying a stream compaction policy."""

    kept_messages: list[dict[str, Any]]
    dropped_messages: list[dict[str, Any]]
    first_kept_index: int
    tokens_before: int


@dataclass(frozen=True)
class StreamCompactionPolicy:
    """Policy for trimming long-running stream context windows."""

    enabled: bool
    settings: CompactionSettings

    @classmethod
    def from_settings(cls, settings: Settings) -> StreamCompactionPolicy:
        """Build a policy from runtime settings."""
        return cls(
            enabled=settings.stream_compaction_enabled,
            settings=CompactionSettings(
                reserve_tokens=settings.compaction_reserve_tokens,
                keep_recent_tokens=settings.compaction_keep_recent_tokens,
            ),
        )

    def apply(self, messages: list[dict[str, Any]]) -> StreamCompactionDecision:
        """Return a trimmed context window for streaming prompts."""
        if not self.enabled or not messages:
            tokens_before = sum(estimate_message_tokens(message) for message in messages)
            return StreamCompactionDecision(
                kept_messages=messages,
                dropped_messages=[],
                first_kept_index=0,
                tokens_before=tokens_before,
            )
        preparation = prepare_compaction(messages, settings=self.settings)
        return StreamCompactionDecision(
            kept_messages=preparation.kept_messages,
            dropped_messages=preparation.messages_to_summarize,
            first_kept_index=preparation.first_kept_index,
            tokens_before=preparation.tokens_before,
        )
