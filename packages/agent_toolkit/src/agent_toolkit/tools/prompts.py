from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from agent_toolkit.tools.mcp_http import MCPHttpClient


@dataclass(frozen=True)
class PromptDefinition:
    """Prompt definition returned from MCP."""

    name: str
    title: str
    description: str
    arguments: list[dict[str, Any]]


class MCPPromptClient:
    """Minimal MCP prompts client."""

    def __init__(self, base_url: str) -> None:
        """Initialize the MCP prompts client."""
        self._client = MCPHttpClient(base_url)

    async def close(self) -> None:
        """Close the underlying MCP client."""
        await self._client.close()

    async def list_prompts(self) -> list[PromptDefinition]:
        """List prompt definitions available from MCP."""
        result = await self._client.request("prompts/list")
        prompts = result.get("prompts", [])
        return [
            PromptDefinition(
                name=prompt.get("name", ""),
                title=prompt.get("title", ""),
                description=prompt.get("description", ""),
                arguments=prompt.get("arguments", []),
            )
            for prompt in prompts
        ]

    async def get_prompt(
        self, name: str, arguments: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Fetch a prompt template by name."""
        return await self._client.request(
            "prompts/get",
            {"name": name, "arguments": arguments or {}},
        )
