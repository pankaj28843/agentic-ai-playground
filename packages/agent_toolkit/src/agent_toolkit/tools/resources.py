from __future__ import annotations

from typing import Any

from agent_toolkit.tools.mcp_http import MCPHttpClient


class MCPResourceClient:
    """Minimal MCP resources client."""

    def __init__(self, base_url: str) -> None:
        """Initialize the MCP resources client."""
        self._client = MCPHttpClient(base_url)

    async def close(self) -> None:
        """Close the underlying MCP client."""
        await self._client.close()

    async def list_resources(self) -> list[dict[str, Any]]:
        """List resources exposed by the MCP server."""
        result = await self._client.request("resources/list")
        return result.get("resources", [])

    async def read_resource(self, uri: str) -> list[dict[str, Any]]:
        """Read resource contents by URI."""
        result = await self._client.request("resources/read", {"uri": uri})
        return result.get("contents", [])
