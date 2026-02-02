"""MCP client providers - convenience functions for common MCP operations.

This module provides convenience functions built on top of the registry.
For direct registry access, use:
    from agent_toolkit.mcp.registry import get_client, list_providers

Primary entry points:
    get_techdocs_client() - Get a TechDocs MCP client
    shutdown_mcp_clients() - Clean up MCP resources
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agent_toolkit.mcp.registry import (
    get_client,
    get_registry,
    reset_registry,
)

if TYPE_CHECKING:
    from strands.tools.mcp import MCPClient

    from agent_toolkit.mcp.config import MCPProviderConfig

logger = logging.getLogger(__name__)


def get_techdocs_client() -> MCPClient:
    """Get a fresh TechDocs MCP client.

    This is the primary entry point for TechDocs MCP integration.
    Returns a new MCPClient each call - pass directly to Agent(tools=[client]).

    Raises:
        ValueError: If techdocs provider is not configured.
    """
    return get_client("techdocs")


def get_techdocs_provider() -> MCPProviderConfig | None:
    """Get the TechDocs provider configuration (for validation/inspection)."""
    return get_registry().get_provider("techdocs")


def shutdown_mcp_clients() -> None:
    """Reset MCP providers (clears cached registry state)."""
    reset_registry()
