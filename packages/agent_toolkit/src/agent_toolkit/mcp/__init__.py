"""MCP (Model Context Protocol) integration for agent toolkit.

This module provides MCP client integration using Strands' native MCPClient.
MCP clients are used as tool providers - tools are discovered dynamically
from the remote server.

Providers are configured via mcp_providers.toml - add new providers by
editing the TOML file without code changes.

Usage:
    from agent_toolkit.mcp import get_client, list_providers

    # Get a specific provider's client (with automatic retry/reconnect)
    client = get_client("techdocs")

    # Pass it directly to Agent - tools are discovered automatically
    agent = Agent(tools=[client, ...other_tools])

    # List all configured providers
    for provider in list_providers():
        print(f"{provider.id}: {provider.name}")

    # Get non-resilient client (for testing or when you want manual control)
    raw_client = get_client("techdocs", resilient=False)

Convenience functions:
    get_techdocs_client() - Equivalent to get_client("techdocs")
    shutdown_mcp_clients() - Clean up MCP resources
"""

from agent_toolkit.mcp.config import MCPProviderConfig
from agent_toolkit.mcp.providers import (
    get_techdocs_client,
    get_techdocs_provider,
    shutdown_mcp_clients,
)
from agent_toolkit.mcp.registry import (
    get_client,
    get_provider,
    get_registry,
    list_providers,
    reset_registry,
)
from agent_toolkit.mcp.resilient_client import ResilientMCPClient

__all__ = [
    "MCPProviderConfig",
    "ResilientMCPClient",
    "get_client",
    "get_provider",
    "get_registry",
    "get_techdocs_client",
    "get_techdocs_provider",
    "list_providers",
    "reset_registry",
    "shutdown_mcp_clients",
]
