from __future__ import annotations

from typing import TYPE_CHECKING

from agent_toolkit.config.service import get_config_service
from agent_toolkit.config.tool_expansion import expand_tools_and_capabilities
from agent_toolkit.models.profiles import AgentProfile, ProfileType

if TYPE_CHECKING:
    from agent_toolkit.config.schema import ConfigSchema
    from agent_toolkit.tools.registry import ToolRegistry

__all__ = ["AgentProfile", "ProfileType", "expand_agent_tools", "load_profiles"]


def load_profiles(
    registry: ToolRegistry | None = None,
) -> dict[str, AgentProfile]:
    """Load atomic agent profiles from the new schema."""
    _ = registry
    service = get_config_service()
    return service.build_profiles()


def expand_agent_tools(
    agent_name: str,
    tool_groups: list[str] | None = None,
    tool_registry: ToolRegistry | None = None,  # kept for future expansion
) -> list[str]:
    """Expand agent tools including tool groups, with optional overrides."""
    service = get_config_service()
    schema = service.get_schema()
    return _expand_agent_tools(agent_name, schema, tool_registry, tool_groups)


def _expand_agent_tools(
    agent_name: str,
    schema: ConfigSchema,
    tool_registry: ToolRegistry | None = None,  # kept for future expansion
    tool_groups_override: list[str] | None = None,
) -> list[str]:
    """Expand agent tools including tool groups."""
    _ = tool_registry
    tools, _ = expand_tools_and_capabilities(schema, agent_name, tool_groups_override)
    return tools
