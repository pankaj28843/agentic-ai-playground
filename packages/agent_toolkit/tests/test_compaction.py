from __future__ import annotations

from dataclasses import dataclass

from agent_toolkit.compaction import (
    CompactionHook,
    CompactionOverride,
    CompactionSettings,
    estimate_tokens,
    extract_file_ops,
    format_structured_summary,
    prepare_branch_summary,
    prepare_compaction,
    run_branch_summary,
    run_compaction,
)


def test_estimate_tokens_returns_minimum_one() -> None:
    assert estimate_tokens("a") == 1
    assert estimate_tokens("") == 0


def test_extract_file_ops_from_tool_calls() -> None:
    messages = [
        {
            "role": "assistant",
            "content": [
                {"type": "tool-call", "toolName": "file_read", "args": {"path": "a.txt"}},
                {"type": "tool-call", "toolName": "file_write", "args": {"path": "b.txt"}},
            ],
        }
    ]
    ops = extract_file_ops(messages)
    assert ops.read_files == ["a.txt"]
    assert ops.modified_files == ["b.txt"]


def test_format_structured_summary_includes_file_ops() -> None:
    summary = format_structured_summary(
        goal="Goal",
        constraints=[],
        done=[],
        in_progress=[],
        blocked=[],
        decisions=[],
        next_steps=[],
        file_ops=type("F", (), {"read_files": ["a"], "modified_files": ["b"]})(),
    )
    assert "<read-files>" in summary
    assert "a" in summary
    assert "<modified-files>" in summary
    assert "b" in summary


def test_prepare_compaction_prefers_user_boundary() -> None:
    messages = [
        {"role": "user", "content": "A"},
        {"role": "assistant", "content": "B"},
        {"role": "assistant", "content": "C"},
        {"role": "user", "content": "D"},
    ]
    prep = prepare_compaction(messages, settings=CompactionSettings(keep_recent_tokens=1))
    assert prep.first_kept_index in (0, 3)
    assert prep.kept_messages


def test_run_compaction_uses_hook_override() -> None:
    messages = [{"role": "user", "content": "A"}]

    @dataclass
    class OverrideHook(CompactionHook):
        def before_compact(self, preparation):
            return CompactionOverride(
                summary="hooked",
                first_kept_index=0,
                tokens_before=preparation.tokens_before,
            )

    result = run_compaction(messages, summarizer=lambda _: "ignored", hooks=[OverrideHook()])
    assert result.summary == "hooked"


def test_branch_summary_roundtrip() -> None:
    entries = [
        {"message": {"role": "user", "content": "X"}},
        {"message": {"role": "assistant", "content": "Y"}},
    ]
    prep = prepare_branch_summary(entries)
    result = run_branch_summary(prep, summarizer=lambda _: "branch")
    assert result.summary == "branch"
    assert "read_files" in result.details
    assert "modified_files" in result.details
