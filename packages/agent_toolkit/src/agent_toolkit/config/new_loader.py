"""New configuration loader with schema validation and orphan detection."""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path  # noqa: TC003 - needed at runtime for file operations
from typing import Any

from agent_toolkit.config.config_paths import get_all_config_paths
from agent_toolkit.config.schema import (
    AtomicAgent,
    ConfigSchema,
    EntrypointType,
    GraphEdge,
    GraphNode,
    GraphTemplate,
    PublicProfile,
    SwarmAgent,
    SwarmTemplate,
    ToolGroup,
    ValidationResult,
)

logger = logging.getLogger(__name__)


def _load_toml_file(path: Path) -> dict[str, Any]:
    """Load TOML file, return empty dict if not found."""
    if not path.exists():
        return {}
    with path.open("rb") as file:
        return tomllib.load(file)


def _load_agents(paths: list[Path]) -> dict[str, AtomicAgent]:
    """Load atomic agents from TOML files."""
    agents: dict[str, AtomicAgent] = {}
    for path in paths:
        data = _load_toml_file(path)
        for name, config in data.get("agents", {}).items():
            agents[name] = AtomicAgent(
                name=name,
                system_prompt=str(config.get("system_prompt", "")),
                model=str(config.get("model", "")),
                tools=list(config.get("tools", [])),
                tool_groups=list(config.get("tool_groups", [])),
                metadata=dict(config.get("metadata", {})),
            )
    return agents


def _load_graphs(paths: list[Path]) -> dict[str, GraphTemplate]:
    """Load graph templates from TOML files."""
    graphs: dict[str, GraphTemplate] = {}
    for path in paths:
        data = _load_toml_file(path)
        for name, config in data.get("graphs", {}).items():
            nodes = [
                GraphNode(
                    name=node["name"],
                    agent=node.get("agent", ""),
                )
                for node in config.get("nodes", [])
            ]
            edges = [
                GraphEdge(from_node=edge["from"], to_node=edge["to"])
                for edge in config.get("edges", [])
            ]
            graphs[name] = GraphTemplate(
                name=name,
                description=str(config.get("description", "")),
                entry_point=str(config.get("entry_point", "")),
                nodes=nodes,
                edges=edges,
                timeouts=dict(config.get("timeouts", {})),
            )
    return graphs


def _load_swarms(paths: list[Path]) -> dict[str, SwarmTemplate]:
    """Load swarm templates from TOML files."""
    swarms: dict[str, SwarmTemplate] = {}
    for path in paths:
        data = _load_toml_file(path)
        for name, config in data.get("swarms", {}).items():
            agents = [
                SwarmAgent(
                    name=agent["name"],
                    agent=agent.get("agent", ""),
                )
                for agent in config.get("agents", [])
            ]
            swarms[name] = SwarmTemplate(
                name=name,
                description=str(config.get("description", "")),
                entry_point=str(config.get("entry_point", "")),
                agents=agents,
                max_handoffs=int(config.get("max_handoffs", 10)),
                max_iterations=int(config.get("max_iterations", 15)),
                timeouts=dict(config.get("timeouts", {})),
            )
    return swarms


def _load_public_profiles(paths: list[Path]) -> dict[str, PublicProfile]:
    """Load public profiles from TOML files."""
    profiles: dict[str, PublicProfile] = {}
    for path in paths:
        data = _load_toml_file(path)
        for name, config in data.get("public_profiles", {}).items():
            entrypoint_type = EntrypointType(config.get("entrypoint_type", "single"))
            profiles[name] = PublicProfile(
                name=name,
                display_name=str(config.get("name", name)),
                description=str(config.get("description", "")),
                entrypoint_type=entrypoint_type,
                entrypoint_reference=str(config.get("entrypoint_reference", "")),
                default=bool(config.get("default", False)),
                metadata=dict(config.get("metadata", {})),
            )
    return profiles


def _load_tool_groups(paths: list[Path]) -> dict[str, ToolGroup]:
    """Load tool groups from TOML files."""
    groups: dict[str, ToolGroup] = {}
    for path in paths:
        data = _load_toml_file(path)
        for name, config in data.get("tool_groups", {}).items():
            groups[name] = ToolGroup(
                name=name,
                description=str(config.get("description", "")),
                tools=list(config.get("tools", [])),
                capabilities=list(config.get("capabilities", [])),
            )
    return groups


def _validate_references(schema: ConfigSchema) -> ValidationResult:  # noqa: C901, PLR0912
    """Validate all references and detect orphaned definitions."""
    errors: list[str] = []
    warnings: list[str] = []

    # Track which agents/graphs/swarms are referenced
    referenced_agents: set[str] = set()
    referenced_graphs: set[str] = set()
    referenced_swarms: set[str] = set()
    referenced_tool_groups: set[str] = set()

    # Validate public profiles
    for profile_name, profile in schema.public_profiles.items():
        if profile.entrypoint_type == EntrypointType.SINGLE:
            if profile.entrypoint_reference not in schema.agents:
                errors.append(
                    f"Public profile '{profile_name}' references unknown agent '{profile.entrypoint_reference}'"
                )
            else:
                referenced_agents.add(profile.entrypoint_reference)
        elif profile.entrypoint_type == EntrypointType.GRAPH:
            if profile.entrypoint_reference not in schema.graphs:
                errors.append(
                    f"Public profile '{profile_name}' references unknown graph '{profile.entrypoint_reference}'"
                )
            else:
                referenced_graphs.add(profile.entrypoint_reference)
        elif profile.entrypoint_type == EntrypointType.SWARM:
            if profile.entrypoint_reference not in schema.swarms:
                errors.append(
                    f"Public profile '{profile_name}' references unknown swarm '{profile.entrypoint_reference}'"
                )
            else:
                referenced_swarms.add(profile.entrypoint_reference)

    # Validate graph node references
    for graph_name, graph in schema.graphs.items():
        for node in graph.nodes:
            if node.agent not in schema.agents:
                errors.append(
                    f"Graph '{graph_name}' node '{node.name}' references unknown agent '{node.agent}'"
                )
            else:
                referenced_agents.add(node.agent)

        # Validate entry point exists as a node
        if graph.entry_point not in [node.name for node in graph.nodes]:
            errors.append(
                f"Graph '{graph_name}' entry_point '{graph.entry_point}' is not a defined node"
            )

    # Validate swarm agent references
    for swarm_name, swarm in schema.swarms.items():
        for agent in swarm.agents:
            if agent.agent not in schema.agents:
                errors.append(
                    f"Swarm '{swarm_name}' agent '{agent.name}' references unknown agent '{agent.agent}'"
                )
            else:
                referenced_agents.add(agent.agent)

        # Validate entry point exists as an agent
        if swarm.entry_point not in [agent.name for agent in swarm.agents]:
            errors.append(
                f"Swarm '{swarm_name}' entry_point '{swarm.entry_point}' is not a defined agent"
            )

    # Validate agent tool group references
    for agent_name, agent in schema.agents.items():
        for tool_group in agent.tool_groups:
            if tool_group not in schema.tool_groups:
                errors.append(f"Agent '{agent_name}' references unknown tool group '{tool_group}'")
            else:
                referenced_tool_groups.add(tool_group)

    # Check for orphaned definitions
    orphaned_agents = set(schema.agents.keys()) - referenced_agents
    if orphaned_agents:
        warnings.append(
            f"Orphaned agents (not referenced by any profile/graph/swarm): {', '.join(sorted(orphaned_agents))}"
        )

    orphaned_graphs = set(schema.graphs.keys()) - referenced_graphs
    if orphaned_graphs:
        warnings.append(
            f"Orphaned graphs (not referenced by any public profile): {', '.join(sorted(orphaned_graphs))}"
        )

    orphaned_swarms = set(schema.swarms.keys()) - referenced_swarms
    if orphaned_swarms:
        warnings.append(
            f"Orphaned swarms (not referenced by any public profile): {', '.join(sorted(orphaned_swarms))}"
        )

    orphaned_tool_groups = set(schema.tool_groups.keys()) - referenced_tool_groups
    if orphaned_tool_groups:
        warnings.append(
            f"Orphaned tool groups (not referenced by any agent): {', '.join(sorted(orphaned_tool_groups))}"
        )

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


class NewConfigLoader:
    """Load configuration using new schema with validation."""

    def load(self) -> tuple[ConfigSchema, ValidationResult]:
        """Load and validate configuration from files."""
        # Get config paths for all file types
        agent_paths = get_all_config_paths("agents")
        graph_paths = get_all_config_paths("graphs")
        swarm_paths = get_all_config_paths("swarms")
        profile_paths = get_all_config_paths("public_profiles")
        tool_group_paths = get_all_config_paths("tool_groups")

        # Load all configuration sections
        agents = _load_agents(agent_paths)
        graphs = _load_graphs(graph_paths)
        swarms = _load_swarms(swarm_paths)
        public_profiles = _load_public_profiles(profile_paths)
        tool_groups = _load_tool_groups(tool_group_paths)

        # Create schema
        schema = ConfigSchema(
            agents=agents,
            graphs=graphs,
            swarms=swarms,
            public_profiles=public_profiles,
            tool_groups=tool_groups,
        )

        # Validate references and detect orphans
        validation = _validate_references(schema)

        # Log validation results
        if validation.errors:
            for error in validation.errors:
                logger.error("Config validation error: %s", error)

        if validation.warnings:
            for warning in validation.warnings:
                logger.warning("Config validation warning: %s", warning)

        return schema, validation
