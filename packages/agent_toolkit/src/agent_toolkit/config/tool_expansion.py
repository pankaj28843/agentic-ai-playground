"""Helper functions for expanding agent tools from config schema."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_toolkit.utils import dedupe

if TYPE_CHECKING:
    from agent_toolkit.config.schema import ConfigSchema


def expand_tools_and_capabilities(
    schema: ConfigSchema,
    agent_name: str,
    tool_groups_override: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Expand tool groups and return unique tool names and capabilities."""
    agent = schema.agents.get(agent_name)
    if not agent:
        return [], []

    tools = list(agent.tools)
    tool_groups = tool_groups_override if tool_groups_override is not None else agent.tool_groups
    capabilities: list[str] = []

    for group_name in tool_groups:
        group = schema.tool_groups.get(group_name)
        if group:
            tools.extend(group.tools)
            capabilities.extend(group.capabilities)

    return dedupe(tools), dedupe(capabilities)
