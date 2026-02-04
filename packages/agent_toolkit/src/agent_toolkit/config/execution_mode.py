"""Runtime execution mode resolution using new configuration schema."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_toolkit.config.service import ConfigService, get_config_service

if TYPE_CHECKING:
    from agent_toolkit.tools.registry import ToolRegistry


class ExecutionModeResolver:
    """Resolve execution modes from public profile configuration."""

    def __init__(
        self, tool_registry: ToolRegistry | None = None, service: ConfigService | None = None
    ) -> None:
        self._tool_registry = tool_registry
        self._service = service or get_config_service()

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
        return self._service.resolve_execution_mode(profile_name)

    def get_public_profiles(self) -> dict[str, dict[str, Any]]:
        """Get all public profiles with their metadata."""
        return self._service.list_public_profiles()

    def get_default_profile(self) -> str | None:
        """Get the default public profile name (if configured)."""
        schema = self._service.get_schema()
        sorted_profiles = sorted(
            schema.public_profiles.items(),
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
        return self._service.get_graph_template(template_name)

    def get_swarm_template(self, template_name: str) -> dict[str, Any] | None:
        """Get swarm template configuration."""
        return self._service.get_swarm_template(template_name)


# Global resolver instance
_resolver: ExecutionModeResolver | None = None


def get_execution_mode_resolver(tool_registry: ToolRegistry | None = None) -> ExecutionModeResolver:
    """Get or create the global execution mode resolver."""
    global _resolver  # noqa: PLW0603
    if _resolver is None:
        _resolver = ExecutionModeResolver(tool_registry)
    return _resolver
