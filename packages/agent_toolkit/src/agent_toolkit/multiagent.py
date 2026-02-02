from __future__ import annotations

import logging
import tomllib
from typing import TYPE_CHECKING, Any

from strands.multiagent import GraphBuilder, Swarm

from agent_toolkit.agents import AgentFactory
from agent_toolkit.config import load_profiles
from agent_toolkit.config.config_paths import resolve_config_path
from agent_toolkit.mcp.client_resolver import get_mcp_clients_for_profile
from agent_toolkit.tools import DEFAULT_TOOL_REGISTRY

if TYPE_CHECKING:
    from strands import Agent

    from agent_toolkit.config import Settings
    from agent_toolkit.config.swarm_presets import SwarmPreset

logger = logging.getLogger(__name__)


def _load_graph_templates() -> dict[str, dict[str, Any]]:
    path = resolve_config_path("graphs")
    if not path.exists():
        return {}
    with path.open("rb") as file:
        data = tomllib.load(file)
    return {name: dict(value) for name, value in data.get("graphs", {}).items()}


def _load_swarm_templates() -> dict[str, dict[str, Any]]:
    path = resolve_config_path("swarms")
    if not path.exists():
        return {}
    with path.open("rb") as file:
        data = tomllib.load(file)
    return {name: dict(value) for name, value in data.get("swarms", {}).items()}


def _load_profiles_for_settings(_settings: Settings) -> dict[str, Any]:
    # No longer need to parse profile_dirs - config_paths handles it
    return load_profiles()


def build_graph(
    settings: Settings,
    session_manager: Any = None,
    template_name: str = "default",
    trace_attributes: dict[str, str] | None = None,
) -> Any:
    """Build a deterministic Graph orchestrator from templates.

    Uses template_name to select which graph configuration to use.
    Raises ValueError if the requested template doesn't exist.

    Supports model_override per node to use different models than profile default.
    """
    templates = _load_graph_templates()
    template = templates.get(template_name)
    if template is None:
        available = list(templates.keys())
        msg = f"Unknown graph template: {template_name}. Available: {available}"
        raise ValueError(msg)

    profiles = _load_profiles_for_settings(settings)
    factory = AgentFactory(settings=settings, registry=DEFAULT_TOOL_REGISTRY)

    builder = GraphBuilder()
    for node in template.get("nodes", []):
        node_name = node.get("name")
        agent_name = node.get("agent")
        model_override = node.get("model_override")
        if not node_name or not agent_name:
            msg = "Graph template node missing name/agent"
            raise ValueError(msg)
        profile = profiles.get(agent_name)
        if profile is None:
            msg = f"Unknown agent in graph template: {agent_name}"
            raise ValueError(msg)

        # Apply model override if specified
        if model_override:
            profile = profile.model_copy(update={"model": model_override})

        mcp_clients = get_mcp_clients_for_profile(profile)
        agent = factory.create_from_profile(
            profile,
            use_session_manager=False,
            use_conversation_manager=False,
            mcp_clients=mcp_clients if mcp_clients else None,
            trace_attributes=trace_attributes,
        )
        builder.add_node(agent, node_name)

    for edge in template.get("edges", []):
        source = edge.get("from")
        target = edge.get("to")
        if not source or not target:
            msg = "Graph template edge missing from/to"
            raise ValueError(msg)
        builder.add_edge(source, target)

    entry_point = template.get("entry_point") or ""
    if not entry_point:
        msg = "Graph template missing entry_point"
        raise ValueError(msg)
    builder.set_entry_point(entry_point)

    timeouts = template.get("timeouts", {})
    builder.set_execution_timeout(timeouts.get("execution", settings.graph_execution_timeout))
    builder.set_node_timeout(timeouts.get("node", settings.graph_node_timeout))

    graph = builder.build()
    if session_manager is not None:
        if hasattr(graph, "session_manager"):
            graph.session_manager = session_manager
        if hasattr(graph, "hooks"):
            graph.hooks.add_hook(session_manager)
    return graph


def build_swarm(
    settings: Settings,
    session_manager: Any = None,
    preset: SwarmPreset | None = None,
    template_name: str = "default",
    trace_attributes: dict[str, str] | None = None,
) -> Swarm:
    """Build a Swarm orchestrator from templates.

    Uses template_name to select which swarm configuration to use.
    Raises ValueError if the requested template doesn't exist.

    Supports model_override per agent to use different models than profile default.
    """
    templates = _load_swarm_templates()
    template = templates.get(template_name)
    if template is None:
        available = list(templates.keys())
        msg = f"Unknown swarm template: {template_name}. Available: {available}"
        raise ValueError(msg)

    logger.info("Building swarm from template: %s", template_name)
    profiles = _load_profiles_for_settings(settings)
    factory = AgentFactory(settings=settings, registry=DEFAULT_TOOL_REGISTRY)

    agents: list[Agent] = []
    for agent_spec in template.get("agents", []):
        agent_name = agent_spec.get("name")
        profile_name = agent_spec.get("agent")
        model_override = agent_spec.get("model_override")
        if not agent_name or not profile_name:
            msg = "Swarm template agent missing name/agent"
            raise ValueError(msg)
        profile = profiles.get(profile_name)
        if profile is None:
            msg = f"Unknown agent in swarm template: {profile_name}"
            raise ValueError(msg)

        # Apply model override if specified
        if model_override:
            profile = profile.model_copy(update={"model": model_override})

        mcp_clients = get_mcp_clients_for_profile(profile)
        logger.info(
            "Swarm agent '%s' (profile=%s, model=%s): %d MCP clients, tool_groups=%s",
            agent_name,
            profile_name,
            profile.model,
            len(mcp_clients),
            profile.tool_groups,
        )
        agent = factory.create_from_profile(
            profile,
            use_session_manager=False,
            use_conversation_manager=False,
            mcp_clients=mcp_clients if mcp_clients else None,
            trace_attributes=trace_attributes,
        )
        agent.name = agent_name
        agents.append(agent)

    if not agents:
        msg = "Swarm template has no agents"
        raise ValueError(msg)
    entry_name = template.get("entry_point") or agents[0].name
    entry_agent = next((agent for agent in agents if agent.name == entry_name), agents[0])

    max_handoffs = (
        preset.max_handoffs if preset else template.get("max_handoffs", settings.swarm_max_handoffs)
    )
    max_iterations = (
        preset.max_iterations
        if preset
        else template.get("max_iterations", settings.swarm_max_iterations)
    )
    timeouts = template.get("timeouts", {})
    execution_timeout = (
        preset.execution_timeout
        if preset
        else timeouts.get("execution", settings.swarm_execution_timeout)
    )
    node_timeout = (
        preset.node_timeout if preset else timeouts.get("node", settings.swarm_node_timeout)
    )

    return Swarm(
        agents,
        entry_point=entry_agent,
        max_handoffs=max_handoffs,
        max_iterations=max_iterations,
        execution_timeout=execution_timeout,
        node_timeout=node_timeout,
        session_manager=session_manager,
    )
