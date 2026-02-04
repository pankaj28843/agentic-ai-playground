"""Compaction and branch summary pipeline utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterable

from agent_toolkit.compaction.models import (
    BranchSummaryPreparation,
    BranchSummaryResult,
    CompactionHook,
    CompactionOverride,
    CompactionPreparation,
    CompactionResult,
    CompactionSettings,
    Summarizer,
)
from agent_toolkit.compaction.utils import estimate_message_tokens, extract_file_ops


def prepare_compaction(
    messages: list[dict[str, Any]],
    settings: CompactionSettings | None = None,
) -> CompactionPreparation:
    """Split messages into kept and summarized segments based on token budget."""
    settings = settings or CompactionSettings()
    token_counts = [estimate_message_tokens(message) for message in messages]
    total_tokens = sum(token_counts)

    if not messages:
        return CompactionPreparation(
            messages_to_summarize=[],
            kept_messages=[],
            first_kept_index=0,
            tokens_before=0,
            file_ops=extract_file_ops([]),
        )

    # Keep recent messages within budget
    running_tokens = 0
    cut_index = len(messages)
    for idx in range(len(messages) - 1, -1, -1):
        running_tokens += token_counts[idx]
        if running_tokens >= settings.keep_recent_tokens:
            cut_index = idx
            break

    if cut_index == len(messages):
        cut_index = 0

    # Prefer cutting at user message boundary
    while cut_index > 0 and messages[cut_index].get("role") != "user":
        cut_index -= 1

    messages_to_summarize = messages[:cut_index]
    kept_messages = messages[cut_index:]
    file_ops = extract_file_ops(messages_to_summarize)

    return CompactionPreparation(
        messages_to_summarize=messages_to_summarize,
        kept_messages=kept_messages,
        first_kept_index=cut_index,
        tokens_before=total_tokens,
        file_ops=file_ops,
    )


def run_compaction(
    messages: list[dict[str, Any]],
    summarizer: Summarizer,
    settings: CompactionSettings | None = None,
    hooks: Iterable[CompactionHook] | None = None,
) -> CompactionResult:
    """Run compaction with optional hook overrides."""
    preparation = prepare_compaction(messages, settings=settings)

    for hook in hooks or []:
        override = hook.before_compact(preparation)
        if isinstance(override, CompactionOverride):
            return CompactionResult(
                summary=override.summary,
                first_kept_index=override.first_kept_index,
                tokens_before=override.tokens_before,
                details=override.details,
            )

    summary = summarizer(preparation.messages_to_summarize)
    return CompactionResult(
        summary=summary,
        first_kept_index=preparation.first_kept_index,
        tokens_before=preparation.tokens_before,
        details={
            "read_files": preparation.file_ops.read_files,
            "modified_files": preparation.file_ops.modified_files,
        },
    )


def prepare_branch_summary(entries: list[dict[str, Any]]) -> BranchSummaryPreparation:
    """Prepare a branch summary payload from session entries."""
    messages: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if "message" in entry and isinstance(entry["message"], dict):
            messages.append(entry["message"])
        else:
            messages.append(entry)
    tokens_before = sum(estimate_message_tokens(message) for message in messages)
    file_ops = extract_file_ops(messages)
    return BranchSummaryPreparation(
        entries_to_summarize=entries,
        tokens_before=tokens_before,
        file_ops=file_ops,
    )


def run_branch_summary(
    preparation: BranchSummaryPreparation,
    summarizer: Summarizer,
) -> BranchSummaryResult:
    """Run branch summarization."""
    summary = summarizer(preparation.entries_to_summarize)
    return BranchSummaryResult(
        summary=summary,
        details={
            "read_files": preparation.file_ops.read_files,
            "modified_files": preparation.file_ops.modified_files,
        },
    )
