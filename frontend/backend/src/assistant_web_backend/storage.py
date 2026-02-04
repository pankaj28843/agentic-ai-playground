from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ThreadRecord:
    """Serialized thread metadata stored in SQLite."""

    remote_id: str
    title: str | None
    status: str
    created_at: str
    updated_at: str
    model_override: str | None = None
    tool_groups_override: list[str] | None = None


@dataclass(frozen=True)
class MessageRecord:
    """Serialized message record stored in SQLite."""

    message_id: str
    thread_id: str
    role: str
    content: list[dict[str, Any]]
    created_at: str
    phoenix_trace_id: str | None = None
    # New fields for run metadata
    run_profile: str | None = None
    run_mode: str | None = None
    execution_mode: str | None = None
    entrypoint_reference: str | None = None
    model_id: str | None = None
    phoenix_session_id: str | None = None
    session_entry_id: str | None = None


class Storage:
    """SQLite-backed storage for threads and messages."""

    def __init__(self, db_path: str | Path) -> None:
        """Initialize storage and ensure tables exist."""
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def list_threads(self) -> list[ThreadRecord]:
        """Return all threads ordered by most recent update."""
        rows = self._fetch_all(
            """SELECT id, title, status, created_at, updated_at, model_override,
                      tool_groups_override
               FROM threads ORDER BY updated_at DESC"""
        )
        return [
            ThreadRecord(
                remote_id=row[0],
                title=row[1],
                status=row[2],
                created_at=row[3],
                updated_at=row[4],
                model_override=row[5],
                tool_groups_override=json.loads(row[6]) if row[6] else None,
            )
            for row in rows
        ]

    def create_thread(self, remote_id: str) -> ThreadRecord:
        """Create a thread if it doesn't exist."""
        now = _timestamp()
        existing = self.fetch_thread(remote_id)
        if existing:
            return existing
        self._execute(
            """INSERT INTO threads
               (id, title, status, created_at, updated_at, model_override, tool_groups_override)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (remote_id, None, "regular", now, now, None, None),
        )
        return ThreadRecord(remote_id, None, "regular", now, now, None, None)

    def fetch_thread(self, remote_id: str) -> ThreadRecord | None:
        """Fetch a thread by ID."""
        rows = self._fetch_all(
            """SELECT id, title, status, created_at, updated_at, model_override,
                      tool_groups_override
               FROM threads WHERE id = ?""",
            (remote_id,),
        )
        if not rows:
            return None
        row = rows[0]
        return ThreadRecord(
            remote_id=row[0],
            title=row[1],
            status=row[2],
            created_at=row[3],
            updated_at=row[4],
            model_override=row[5],
            tool_groups_override=json.loads(row[6]) if row[6] else None,
        )

    def update_thread_overrides(
        self,
        remote_id: str,
        model_override: str | None,
        tool_groups_override: list[str] | None,
    ) -> None:
        """Persist override metadata for a thread."""
        tool_groups_value = (
            json.dumps(tool_groups_override, ensure_ascii=True)
            if tool_groups_override is not None
            else None
        )
        self._execute(
            """UPDATE threads
               SET model_override = ?, tool_groups_override = ?, updated_at = ?
               WHERE id = ?""",
            (model_override, tool_groups_value, _timestamp(), remote_id),
        )

    def rename_thread(self, remote_id: str, title: str) -> None:
        """Rename a thread by ID."""
        self._execute(
            "UPDATE threads SET title = ?, updated_at = ? WHERE id = ?",
            (title, _timestamp(), remote_id),
        )

    def archive_thread(self, remote_id: str) -> None:
        """Archive a thread by ID."""
        self._set_status(remote_id, "archived")

    def unarchive_thread(self, remote_id: str) -> None:
        """Unarchive a thread by ID."""
        self._set_status(remote_id, "regular")

    def delete_thread(self, remote_id: str) -> None:
        """Delete a thread and its messages."""
        self._execute("DELETE FROM messages WHERE thread_id = ?", (remote_id,))
        self._execute("DELETE FROM threads WHERE id = ?", (remote_id,))

    def list_messages(self, remote_id: str) -> list[MessageRecord]:
        """Return messages for a thread ordered by creation time."""
        rows = self._fetch_all(
            """SELECT id, thread_id, role, content, created_at, phoenix_trace_id,
                      run_profile, run_mode, execution_mode, entrypoint_reference,
                      model_id, phoenix_session_id, session_entry_id
               FROM messages WHERE thread_id = ? ORDER BY created_at ASC""",
            (remote_id,),
        )
        return [
            MessageRecord(
                message_id=row[0],
                thread_id=row[1],
                role=row[2],
                content=json.loads(row[3]),
                created_at=row[4],
                phoenix_trace_id=row[5],
                run_profile=row[6],
                run_mode=row[7],
                execution_mode=row[8],
                entrypoint_reference=row[9],
                model_id=row[10],
                phoenix_session_id=row[11],
                session_entry_id=row[12],
            )
            for row in rows
        ]

    def append_message(self, record: MessageRecord) -> None:
        """Persist a message to storage."""
        self._execute(
            """INSERT OR REPLACE INTO messages
               (id, thread_id, role, content, created_at, phoenix_trace_id,
                run_profile, run_mode, execution_mode, entrypoint_reference,
                model_id, phoenix_session_id, session_entry_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.message_id,
                record.thread_id,
                record.role,
                json.dumps(record.content, ensure_ascii=True),
                record.created_at,
                record.phoenix_trace_id,
                record.run_profile,
                record.run_mode,
                record.execution_mode,
                record.entrypoint_reference,
                record.model_id,
                record.phoenix_session_id,
                record.session_entry_id,
            ),
        )
        self._execute(
            "UPDATE threads SET updated_at = ? WHERE id = ?",
            (_timestamp(), record.thread_id),
        )

    def _set_status(self, remote_id: str, status: str) -> None:
        self._execute(
            "UPDATE threads SET status = ?, updated_at = ? WHERE id = ?",
            (status, _timestamp(), remote_id),
        )

    def _init_db(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS threads (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    model_override TEXT,
                    tool_groups_override TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    thread_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    phoenix_trace_id TEXT,
                    run_profile TEXT,
                    run_mode TEXT,
                    execution_mode TEXT,
                    entrypoint_reference TEXT,
                    model_id TEXT,
                    phoenix_session_id TEXT,
                    session_entry_id TEXT,
                    FOREIGN KEY (thread_id) REFERENCES threads(id) ON DELETE CASCADE
                )
                """
            )
            _ensure_column(conn, "threads", "model_override", "TEXT")
            _ensure_column(conn, "threads", "tool_groups_override", "TEXT")
            _ensure_column(conn, "messages", "session_entry_id", "TEXT")

    def _fetch_all(self, query: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with sqlite3.connect(self._db_path) as conn:
            cursor = conn.execute(query, params)
            return cursor.fetchall()

    def _execute(self, query: str, params: tuple[Any, ...]) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(query, params)
            conn.commit()


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    cursor = conn.execute(f"PRAGMA table_info({table})")
    existing = {row[1] for row in cursor.fetchall()}
    if column in existing:
        return
    conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
