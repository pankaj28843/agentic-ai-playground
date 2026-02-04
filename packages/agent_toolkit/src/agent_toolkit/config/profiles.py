from __future__ import annotations

from typing import TYPE_CHECKING

from agent_toolkit.config.new_loader import NewConfigLoader
from agent_toolkit.models.profiles import AgentProfile, ProfileType

if TYPE_CHECKING:
    from agent_toolkit.config.schema import ConfigSchema
    from agent_toolkit.tools.registry import ToolRegistry

__all__ = ["AgentProfile", "ProfileType", "expand_agent_tools", "load_profiles"]


def load_profiles(
    registry: ToolRegistry | None = None,
) -> dict[str, AgentProfile]:
    """Load atomic agent profiles from the new schema."""
    loader = NewConfigLoader()
    schema, validation = loader.load()
    if not validation.valid:
        msg = f"Configuration validation failed: {validation.errors}"
        raise ValueError(msg)

    profiles: dict[str, AgentProfile] = {}
    for agent_name, agent in schema.agents.items():
        tools = _expand_agent_tools(agent_name, schema, registry)
        description = str(agent.metadata.get("description", f"Atomic agent: {agent_name}"))
        profiles[agent_name] = AgentProfile(
            name=agent_name,
            description=description,
            model=agent.model,
            system_prompt=agent.system_prompt,
            tools=tools,
            tool_groups=list(agent.tool_groups),
            extends="",
            metadata=agent.metadata,
            constraints={},
            profile_type=ProfileType.INTERNAL,
            model_config=agent.model_config_overrides,
        )
    return profiles


def expand_agent_tools(
    agent_name: str,
    tool_groups: list[str] | None = None,
    tool_registry: ToolRegistry | None = None,  # kept for future expansion
) -> list[str]:
    """Expand agent tools including tool groups, with optional overrides."""
    loader = NewConfigLoader()
    schema, validation = loader.load()
    if not validation.valid:
        msg = f"Configuration validation failed: {validation.errors}"
        raise ValueError(msg)
    return _expand_agent_tools(agent_name, schema, tool_registry, tool_groups)


def _expand_agent_tools(
    agent_name: str,
    schema: ConfigSchema,
    tool_registry: ToolRegistry | None = None,  # kept for future expansion
    tool_groups_override: list[str] | None = None,
) -> list[str]:
    """Expand agent tools including tool groups."""
    _ = tool_registry
    agent = schema.agents.get(agent_name)
    if not agent:
        return []

    all_tools = list(agent.tools)
    tool_groups = tool_groups_override if tool_groups_override is not None else agent.tool_groups
    for group_name in tool_groups:
        group = schema.tool_groups.get(group_name)
        if group:
            all_tools.extend(group.tools)

    seen: set[str] = set()
    unique_tools: list[str] = []
    for tool in all_tools:
        if tool not in seen:
            unique_tools.append(tool)
            seen.add(tool)
    return unique_tools
