from __future__ import annotations

from pathlib import Path


def list_sessions(storage_dir: str) -> list[str]:
    """List session IDs from the FileSessionManager storage directory."""
    path = Path(storage_dir)
    if not path.exists():
        return []
    sessions = [
        entry.name.replace("session_", "", 1)
        for entry in path.iterdir()
        if entry.is_dir() and entry.name.startswith("session_")
    ]
    return sorted(sessions)
