"""Configuration service for agent_toolkit.

Centralizes loading and validation of configuration schema and settings.
Provides a cached snapshot to avoid redundant IO and validation in callers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agent_toolkit.config.new_loader import NewConfigLoader
from agent_toolkit.config.settings import load_settings
from agent_toolkit.models.profiles import AgentProfile, ProfileType

if TYPE_CHECKING:
    from agent_toolkit.models.config import ConfigSchema, ValidationResult
    from agent_toolkit.models.settings import Settings


@dataclass(frozen=True)
class ConfigSnapshot:
    """Immutable snapshot of loaded configuration."""

    settings: Settings
    schema: ConfigSchema
    validation: ValidationResult


class ConfigService:
    """Load, validate, and serve configuration data."""

    def __init__(self) -> None:
        self._loader = NewConfigLoader()
        self._snapshot: ConfigSnapshot | None = None
        self._config_dir: str | None = None

    def load_snapshot(self, *, force: bool = False) -> ConfigSnapshot:
        """Load a configuration snapshot, optionally forcing reload."""
        settings = load_settings()
        current_dir = settings.playground_config_dir
        if self._snapshot is not None and not force and current_dir == self._config_dir:
            return self._snapshot
        schema, validation = self._loader.load()
        self._snapshot = ConfigSnapshot(settings=settings, schema=schema, validation=validation)
        self._config_dir = current_dir
        return self._snapshot

    def get_schema(self) -> ConfigSchema:
        """Return validated configuration schema."""
        snapshot = self.load_snapshot()
        if not snapshot.validation.valid:
            msg = f"Configuration validation failed: {snapshot.validation.errors}"
            raise ValueError(msg)
        return snapshot.schema

    def get_settings(self) -> Settings:
        """Return settings from the cached snapshot."""
        return self.load_snapshot().settings

    def build_profiles(self) -> dict[str, AgentProfile]:
        """Build agent profiles from the schema."""
        schema = self.get_schema()
        profiles: dict[str, AgentProfile] = {}
        for agent_name, agent in schema.agents.items():
            tools = self.expand_agent_tools(agent_name)
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
        self,
        agent_name: str,
        tool_groups_override: list[str] | None = None,
    ) -> list[str]:
        """Expand agent tools and tool groups into a unique list."""
        schema = self.get_schema()
        agent = schema.agents.get(agent_name)
        if not agent:
            return []

        all_tools = list(agent.tools)
        tool_groups = (
            tool_groups_override if tool_groups_override is not None else agent.tool_groups
        )
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

    def resolve_execution_mode(self, profile_name: str) -> tuple[str, str, dict[str, Any]]:
        """Resolve execution mode from a public profile name."""
        schema = self.get_schema()
        public_profile = schema.public_profiles.get(profile_name)
        if not public_profile:
            msg = f"Unknown public profile: {profile_name}"
            raise ValueError(msg)
        execution_mode = public_profile.entrypoint_type.value
        entrypoint_reference = public_profile.entrypoint_reference
        metadata = {
            "profile_name": profile_name,
            "display_name": public_profile.display_name,
            "description": public_profile.description,
            "default": public_profile.default,
            "entrypoint_type": public_profile.entrypoint_type.value,
            "entrypoint_reference": public_profile.entrypoint_reference,
            **public_profile.metadata,
        }
        return execution_mode, entrypoint_reference, metadata

    def list_public_profiles(self) -> dict[str, dict[str, Any]]:
        """Return public profiles for UI consumption."""
        schema = self.get_schema()
        profiles: dict[str, dict[str, Any]] = {}
        for name, profile in schema.public_profiles.items():
            profiles[name] = {
                "id": name,
                "display_name": profile.display_name,
                "description": profile.description,
                "entrypoint_type": profile.entrypoint_type.value,
                "entrypoint_reference": profile.entrypoint_reference,
                "default": profile.default,
                "metadata": profile.metadata,
            }
        return profiles

    def get_graph_template(self, template_name: str) -> dict[str, Any] | None:
        """Return graph template configuration."""
        schema = self.get_schema()
        graph = schema.graphs.get(template_name)
        if not graph:
            return None
        return {
            "name": graph.name,
            "description": graph.description,
            "entry_point": graph.entry_point,
            "nodes": [{"name": node.name, "agent": node.agent} for node in graph.nodes],
            "edges": [{"from": edge.from_node, "to": edge.to_node} for edge in graph.edges],
            "timeouts": graph.timeouts,
        }

    def get_swarm_template(self, template_name: str) -> dict[str, Any] | None:
        """Return swarm template configuration."""
        schema = self.get_schema()
        swarm = schema.swarms.get(template_name)
        if not swarm:
            return None
        return {
            "name": swarm.name,
            "description": swarm.description,
            "entry_point": swarm.entry_point,
            "agents": [{"name": agent.name, "agent": agent.agent} for agent in swarm.agents],
            "max_handoffs": swarm.max_handoffs,
            "max_iterations": swarm.max_iterations,
            "timeouts": swarm.timeouts,
        }


_config_service: ConfigService | None = None


def get_config_service() -> ConfigService:
    """Return the shared ConfigService instance."""
    global _config_service  # noqa: PLW0603
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service
