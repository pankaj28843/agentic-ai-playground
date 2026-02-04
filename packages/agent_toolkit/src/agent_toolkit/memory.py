from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class MemoryConfig:
    """Configuration for memory-backed session managers."""

    session_id: str
    storage_dir: str | None = None
    memory_id: str | None = None
    actor_id: str | None = None
    region_name: str | None = None


def build_memory_session_manager(adapter: str, config: MemoryConfig):
    """Build a session manager for the selected adapter."""
    if adapter == "file":
        from strands.session.file_session_manager import FileSessionManager  # noqa: PLC0415

        return FileSessionManager(session_id=config.session_id, storage_dir=config.storage_dir)

    if adapter == "agentcore":
        from bedrock_agentcore.memory.integrations.strands.config import (  # noqa: PLC0415
            AgentCoreMemoryConfig,
        )
        from bedrock_agentcore.memory.integrations.strands.session_manager import (  # noqa: PLC0415
            AgentCoreMemorySessionManager,
        )

        memory_id = config.memory_id or os.getenv("AGENTCORE_MEMORY_ID", "")
        if not memory_id:
            message = "AgentCore memory requires AGENTCORE_MEMORY_ID or MemoryConfig.memory_id"
            raise RuntimeError(message)
        actor_id = config.actor_id or os.getenv("AGENTCORE_ACTOR_ID", config.session_id)
        region_name = (
            config.region_name
            or os.getenv("AWS_REGION")
            or os.getenv("AWS_DEFAULT_REGION")
            or "eu-central-1"
        )
        memory_config = AgentCoreMemoryConfig(
            memory_id=memory_id,
            session_id=config.session_id,
            actor_id=actor_id,
        )
        return AgentCoreMemorySessionManager(
            agentcore_memory_config=memory_config,
            region_name=region_name,
        )

    return None
