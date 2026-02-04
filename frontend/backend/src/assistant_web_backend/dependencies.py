"""FastAPI dependency injection for shared services.

Provides proper dependency injection instead of module-level singletons,
following FastAPI best practices and enabling easier testing.

Reference: 12-Factor App - Factor 3 (Store config in environment)
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from assistant_web_backend.services.runtime import get_runtime as _get_runtime
from assistant_web_backend.storage import Storage

if TYPE_CHECKING:
    from agent_toolkit import AgentRuntime


def _storage_path() -> Path:
    """Get storage path from environment."""
    base_dir = Path(os.getenv("WEB_STORAGE_DIR", ".data"))
    return base_dir / "assistant_playground.db"


@lru_cache
def get_storage() -> Storage:
    """Get the Storage instance (cached singleton).

    Uses lru_cache for singleton semantics while maintaining
    proper dependency injection pattern.
    """
    return Storage(_storage_path())


def get_runtime() -> AgentRuntime:
    """Get the AgentRuntime instance."""
    return _get_runtime()
