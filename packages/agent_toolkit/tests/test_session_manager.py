from __future__ import annotations

import json
from pathlib import Path

import pytest
from agent_toolkit.session import SessionManager


def test_session_create_and_open_roundtrip(tmp_path: Path) -> None:
    session_path = tmp_path / "session.jsonl"
    manager = SessionManager.create(session_path, cwd="/tmp/project")
    assert manager.path == session_path
    assert manager.header.version == 3

    # Append a message
    message_id = manager.append_message({"role": "user", "content": "hello"})
    assert manager.get_leaf_id() == message_id

    reopened = SessionManager.open(session_path)
    assert reopened.header.version == 3
    assert reopened.get_leaf_id() == message_id
    entries = reopened.get_entries()
    assert len(entries) == 1
    assert entries[0].type == "message"


def test_append_and_branching(tmp_path: Path) -> None:
    session_path = tmp_path / "branch.jsonl"
    manager = SessionManager.create(session_path)

    first = manager.append_message({"role": "user", "content": "first"})
    second = manager.append_message({"role": "assistant", "content": "second"})
    manager.branch(first)
    forked = manager.append_message({"role": "user", "content": "forked"})

    assert manager.get_leaf_id() == forked
    tree = manager.get_tree()
    assert first in tree
    children = {entry.id for entry in manager.get_children(first)}
    assert second in children
    assert forked in children


def test_append_message_with_custom_id_and_parent(tmp_path: Path) -> None:
    session_path = tmp_path / "custom-id.jsonl"
    manager = SessionManager.create(session_path)

    root = manager.append_message({"role": "user", "content": "root"}, entry_id="msg-root")
    child = manager.append_message(
        {"role": "assistant", "content": "child"},
        entry_id="msg-child",
        parent_id=root,
    )

    assert root == "msg-root"
    assert child == "msg-child"
    assert manager.get_entry(child).parent_id == root


def test_append_message_duplicate_id_raises(tmp_path: Path) -> None:
    session_path = tmp_path / "dupe.jsonl"
    manager = SessionManager.create(session_path)
    manager.append_message({"role": "user", "content": "one"}, entry_id="dup")
    with pytest.raises(ValueError, match="Duplicate entry id"):
        manager.append_message({"role": "assistant", "content": "two"}, entry_id="dup")


def test_append_metadata_entries(tmp_path: Path) -> None:
    session_path = tmp_path / "meta.jsonl"
    manager = SessionManager.create(session_path)
    base = manager.append_message({"role": "user", "content": "base"})

    compaction_id = manager.append_compaction("summary", base, 100, details={"readFiles": []})
    branch_id = manager.append_branch_summary("branch", from_id=base)
    custom_id = manager.append_custom_entry("my-ext", data={"x": 1})
    custom_message_id = manager.append_custom_message("my-ext", content="hi", display=True)
    label_id = manager.append_label_change(base, "checkpoint")
    info_id = manager.append_session_info("Session Name")
    model_id = manager.append_model_change("provider", "model")
    thinking_id = manager.append_thinking_level_change("high")

    ids = {
        compaction_id,
        branch_id,
        custom_id,
        custom_message_id,
        label_id,
        info_id,
        model_id,
        thinking_id,
    }
    assert len(ids) == 8

    entries = manager.get_entries()
    types = {entry.type for entry in entries}
    assert {
        "message",
        "compaction",
        "branch_summary",
        "custom",
        "custom_message",
        "label",
        "session_info",
        "model_change",
        "thinking_level_change",
    }.issubset(types)


def test_jsonl_serialization_uses_camel_case(tmp_path: Path) -> None:
    session_path = tmp_path / "serialize.jsonl"
    manager = SessionManager.create(session_path)
    msg_id = manager.append_message({"role": "user", "content": "hello"})
    manager.append_compaction("summary", msg_id, 1)

    lines = session_path.read_text(encoding="utf-8").splitlines()
    assert lines
    header = json.loads(lines[0])
    assert header["type"] == "session"

    entry = json.loads(lines[1])
    assert "parentId" in entry
    assert "parent_id" not in entry
    assert entry["type"] == "message"

    compaction = json.loads(lines[2])
    assert "firstKeptEntryId" in compaction
    assert "tokensBefore" in compaction


def test_get_branch_traverses_to_root(tmp_path: Path) -> None:
    session_path = tmp_path / "branch-path.jsonl"
    manager = SessionManager.create(session_path)
    a = manager.append_message({"role": "user", "content": "a"})
    b = manager.append_message({"role": "assistant", "content": "b"})
    c = manager.append_message({"role": "user", "content": "c"})

    branch = manager.get_branch(c)
    ids = [entry.id for entry in branch]
    assert ids[0] == c
    assert b in ids
    assert a in ids


def test_branch_unknown_id_raises(tmp_path: Path) -> None:
    session_path = tmp_path / "error.jsonl"
    manager = SessionManager.create(session_path)
    with pytest.raises(ValueError, match="Unknown entry id"):
        manager.branch("missing")
