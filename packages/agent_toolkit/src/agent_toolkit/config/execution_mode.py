"""Runtime execution mode resolution using new configuration schema."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agent_toolkit.config.new_loader import NewConfigLoader

if TYPE_CHECKING:
    from agent_toolkit.config.schema import ConfigSchema
    from agent_toolkit.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ExecutionModeResolver:
    """Resolve execution modes from public profile configuration."""

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self._tool_registry = tool_registry
        self._loader = NewConfigLoader()
        self._schema: ConfigSchema | None = None
        self._load_schema()

    def _load_schema(self) -> None:
        """Load configuration schema."""
        try:
            schema, validation = self._loader.load()
            if not validation.valid:
                logger.error("Configuration validation failed: %s", validation.errors)
                msg = f"Configuration validation failed: {validation.errors}"
                raise ValueError(msg)  # noqa: TRY301
            self._schema = schema
        except Exception:
            logger.exception("Failed to load configuration schema")
            raise

    def resolve_execution_mode(self, profile_name: str) -> tuple[str, str, dict[str, Any]]:
        """Resolve execution mode from profile name.

        Args:
            profile_name: Name of the public profile

        Returns:
            Tuple of (execution_mode, entrypoint_reference, metadata)
            - execution_mode: "single", "swarm", or "graph"
            - entrypoint_reference: Name of agent/swarm/graph to execute
            - metadata: Additional metadata from profile
        """
        if not self._schema:
            msg = "Configuration schema not loaded"
            raise RuntimeError(msg)

        public_profile = self._schema.public_profiles.get(profile_name)
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

    def get_public_profiles(self) -> dict[str, dict[str, Any]]:
        """Get all public profiles with their metadata."""
        if not self._schema:
            msg = "Configuration schema not loaded"
            raise RuntimeError(msg)

        profiles: dict[str, dict[str, Any]] = {}
        for name, profile in self._schema.public_profiles.items():
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

    def get_default_profile(self) -> str | None:
        """Get the default public profile name (if configured)."""
        if not self._schema:
            msg = "Configuration schema not loaded"
            raise RuntimeError(msg)

        sorted_profiles = sorted(
            self._schema.public_profiles.items(),
            key=lambda item: (item[1].metadata.get("ui_order", 999), item[0]),
        )
        defaults = [name for name, profile in sorted_profiles if profile.default]
        if defaults:
            return defaults[0]
        if sorted_profiles:
            return sorted_profiles[0][0]
        return None

    def get_graph_template(self, template_name: str) -> dict[str, Any] | None:
        """Get graph template configuration."""
        if not self._schema:
            return None

        graph = self._schema.graphs.get(template_name)
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
        """Get swarm template configuration."""
        if not self._schema:
            return None

        swarm = self._schema.swarms.get(template_name)
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


# Global resolver instance
_resolver: ExecutionModeResolver | None = None


def get_execution_mode_resolver(tool_registry: ToolRegistry | None = None) -> ExecutionModeResolver:
    """Get or create the global execution mode resolver."""
    global _resolver  # noqa: PLW0603
    if _resolver is None:
        _resolver = ExecutionModeResolver(tool_registry)
    return _resolver
