from __future__ import annotations

from dataclasses import dataclass

try:
    from bedrock_agentcore_sdk.sessions import AgentCoreMemorySessionManager
except ImportError:  # pragma: no cover - optional dependency
    AgentCoreMemorySessionManager = None

try:
    from strands.session.file_session_manager import FileSessionManager
except ImportError:  # pragma: no cover - optional dependency
    FileSessionManager = None


@dataclass(frozen=True)
class MemoryConfig:
    """Configuration for memory-backed session managers."""

    session_id: str
    storage_dir: str | None = None


def build_memory_session_manager(adapter: str, config: MemoryConfig):
    """Build a session manager for the selected adapter."""
    if adapter == "file":
        if FileSessionManager is None:
            message = "File session manager is not available"
            raise RuntimeError(message)
        return FileSessionManager(session_id=config.session_id, storage_dir=config.storage_dir)

    if adapter == "agentcore":
        if AgentCoreMemorySessionManager is None:
            message = "AgentCore memory session manager is not installed"
            raise RuntimeError(message)
        return AgentCoreMemorySessionManager(session_id=config.session_id)

    return None
