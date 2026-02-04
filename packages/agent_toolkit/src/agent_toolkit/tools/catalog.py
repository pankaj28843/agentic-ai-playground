"""Tool catalog with capability-aware expansion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agent_toolkit.config.service import ConfigService, get_config_service
from agent_toolkit.config.tool_expansion import expand_tools_and_capabilities

if TYPE_CHECKING:
    from agent_toolkit.tools.registry import ToolRegistry


@dataclass(frozen=True)
class ToolSelection:
    """Resolved tool names and aggregated capabilities."""

    tools: list[str]
    capabilities: tuple[str, ...]


class ToolCatalog:
    """Resolve tools and tool groups from configuration and registry."""

    def __init__(
        self,
        registry: ToolRegistry,
        config_service: ConfigService | None = None,
    ) -> None:
        self._registry = registry
        self._config_service = config_service or get_config_service()

    def expand_tools(
        self,
        agent_name: str,
        tool_groups_override: list[str] | None = None,
    ) -> ToolSelection:
        """Expand tool groups and return tools plus capabilities."""
        schema = self._config_service.get_schema()
        tools, capabilities = expand_tools_and_capabilities(
            schema,
            agent_name,
            tool_groups_override,
        )
        unique_tools = tools
        unique_capabilities = tuple(capabilities)
        return ToolSelection(tools=unique_tools, capabilities=unique_capabilities)

    def resolve_strands_tools(self, tool_names: list[str]) -> list[Any]:
        """Resolve tool callables for Strands execution."""
        return self._registry.to_strands_tools(tool_names)

    def registry(self) -> ToolRegistry:
        """Return the underlying tool registry."""
        return self._registry
