"""Tool catalog with capability-aware expansion."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agent_toolkit.config.service import ConfigService, get_config_service

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
        agent = schema.agents.get(agent_name)
        if not agent:
            return ToolSelection(tools=[], capabilities=())

        tools = list(agent.tools)
        tool_groups = (
            tool_groups_override if tool_groups_override is not None else agent.tool_groups
        )
        capabilities: list[str] = []

        for group_name in tool_groups:
            group = schema.tool_groups.get(group_name)
            if group:
                tools.extend(group.tools)
                capabilities.extend(group.capabilities)

        unique_tools = _dedupe(tools)
        unique_capabilities = tuple(_dedupe(capabilities))
        return ToolSelection(tools=unique_tools, capabilities=unique_capabilities)

    def resolve_strands_tools(self, tool_names: list[str]) -> list[Any]:
        """Resolve tool callables for Strands execution."""
        return self._registry.to_strands_tools(tool_names)

    def registry(self) -> ToolRegistry:
        """Return the underlying tool registry."""
        return self._registry


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique
