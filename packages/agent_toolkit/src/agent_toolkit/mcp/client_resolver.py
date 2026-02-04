"""Resolve MCP clients for agent profiles based on tool_group capabilities.

This module consolidates the logic for determining which MCP clients
an agent needs based on its profile's tool_groups configuration.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import TYPE_CHECKING, Any

from agent_toolkit.config.service import get_config_service
from agent_toolkit.mcp.registry import get_client

if TYPE_CHECKING:
    from agent_toolkit.config import AgentProfile

logger = logging.getLogger(__name__)


def get_mcp_clients_for_profile(profile: AgentProfile) -> list[Any]:
    """Get MCP clients needed for a profile based on its tool_groups capabilities.

    Inspects the profile's tool_groups and returns MCPClient instances for
    any groups with mcp:* capabilities.

    Args:
        profile: The agent profile to inspect for MCP requirements.

    Returns:
        List of MCPClient instances needed by the profile.
    """
    mcp_clients: list[Any] = []
    tool_groups = _load_tool_groups()
    added_providers: set[str] = set()  # Track which providers we've added

    for group_name in getattr(profile, "tool_groups", []):
        group = tool_groups.get(group_name)
        if group is None:
            continue

        # Check for any mcp:* capability and create corresponding client
        for capability in group.capabilities:
            if capability.startswith("mcp:"):
                provider_id = capability.split(":", 1)[1]  # Extract provider ID
                if provider_id in added_providers:
                    continue  # Don't add same provider twice

                try:
                    client = get_client(provider_id)
                    mcp_clients.append(client)
                    added_providers.add(provider_id)
                    logger.info("Injected %s MCPClient for profile %s", provider_id, profile.name)
                except Exception:  # noqa: BLE001 - graceful fallback
                    logger.debug("%s MCP client unavailable", provider_id, exc_info=True)

    return mcp_clients


@lru_cache(maxsize=1)
def _load_tool_groups() -> dict[str, Any]:
    schema = get_config_service().get_schema()
    return schema.tool_groups
