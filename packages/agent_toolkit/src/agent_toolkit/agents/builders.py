"""Agent runtime builders for session and conversation managers.

These functions create runtime components used by agents. They're separate
from config loading (which happens in config/) - these build actual instances.

Usage:
    from agent_toolkit.agents.builders import (
        build_conversation_manager,
        build_session_manager,
    )

    # In agent factory or runtime
    cm = build_conversation_manager(settings)
    sm = build_session_manager(settings, session_id)
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from strands.agent.conversation_manager.sliding_window_conversation_manager import (
    SlidingWindowConversationManager,
)
from strands.agent.conversation_manager.summarizing_conversation_manager import (
    SummarizingConversationManager,
)

from agent_toolkit.memory import MemoryConfig, build_memory_session_manager

if TYPE_CHECKING:
    from agent_toolkit.config import Settings


def build_conversation_manager(settings: Settings) -> object:
    """Build the configured conversation manager instance.

    Supports:
    - "sliding": SlidingWindowConversationManager with configurable truncation
    - "summarizing": SummarizingConversationManager for intelligent compaction
    """
    if settings.conversation_manager == "summarizing":
        return SummarizingConversationManager(
            summary_ratio=settings.summary_ratio,
            preserve_recent_messages=settings.preserve_recent_messages,
        )
    # Default to sliding window with truncation support
    return SlidingWindowConversationManager(
        window_size=settings.sliding_window_size,
        should_truncate_results=settings.should_truncate_tool_results,
    )


def build_session_manager(settings: Settings, session_id: str) -> object | None:
    """Build a session manager if configured."""
    storage_dir = settings.session_storage_dir or None
    if storage_dir:
        Path(storage_dir).mkdir(parents=True, exist_ok=True)
    adapter = settings.session_manager
    if adapter == "none":
        return None
    return build_memory_session_manager(
        adapter,
        MemoryConfig(session_id=session_id, storage_dir=storage_dir),
    )
