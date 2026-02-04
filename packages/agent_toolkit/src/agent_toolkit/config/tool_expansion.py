"""Helper functions for expanding agent tools from config schema."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_toolkit.utils import dedupe

if TYPE_CHECKING:
    from agent_toolkit.config.schema import AtomicAgent, ConfigSchema, ToolGroup


def resolve_agent(schema: ConfigSchema, agent_name: str) -> AtomicAgent | None:
    """Return the atomic agent definition if present."""
    return schema.agents.get(agent_name)


def resolve_tool_groups(
    schema: ConfigSchema,
    agent_name: str,
    tool_groups_override: list[str] | None = None,
) -> list[tuple[str, ToolGroup]]:
    """Resolve tool group definitions for an agent."""
    agent = resolve_agent(schema, agent_name)
    if not agent:
        return []

    tool_group_names = (
        tool_groups_override if tool_groups_override is not None else agent.tool_groups
    )
    resolved: list[tuple[str, ToolGroup]] = []
    for group_name in tool_group_names:
        group = schema.tool_groups.get(group_name)
        if group:
            resolved.append((group_name, group))
    return resolved


def expand_tools_and_capabilities(
    schema: ConfigSchema,
    agent_name: str,
    tool_groups_override: list[str] | None = None,
    resolved_groups: list[tuple[str, ToolGroup]] | None = None,
) -> tuple[list[str], list[str]]:
    """Expand tool groups and return unique tool names and capabilities."""
    agent = resolve_agent(schema, agent_name)
    if not agent:
        return [], []

    tools = list(agent.tools)
    groups = resolved_groups
    if groups is None:
        groups = resolve_tool_groups(schema, agent_name, tool_groups_override)
    capabilities: list[str] = []

    for _, group in groups:
        tools.extend(group.tools)
        capabilities.extend(group.capabilities)

    return dedupe(tools), dedupe(capabilities)
