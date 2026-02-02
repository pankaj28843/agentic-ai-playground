from __future__ import annotations

from typing import TYPE_CHECKING

from agent_toolkit.config.new_loader import NewConfigLoader
from agent_toolkit.models.profiles import AgentProfile, ProfileType

if TYPE_CHECKING:
    from agent_toolkit.config.schema import ConfigSchema
    from agent_toolkit.tools.registry import ToolRegistry

__all__ = ["AgentProfile", "ProfileType", "load_profiles"]


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


def _expand_agent_tools(
    agent_name: str,
    schema: ConfigSchema,
    tool_registry: ToolRegistry | None = None,  # kept for future expansion
) -> list[str]:
    """Expand agent tools including tool groups."""
    _ = tool_registry
    agent = schema.agents.get(agent_name)
    if not agent:
        return []

    all_tools = list(agent.tools)
    for group_name in agent.tool_groups:
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
