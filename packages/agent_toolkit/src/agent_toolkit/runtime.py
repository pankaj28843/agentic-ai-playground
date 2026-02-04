"""Runtime facade for executing agent requests.

Provides a small surface area that wires configuration, tool catalog, execution
pipeline, and telemetry. The heavy lifting happens in application services.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agent_toolkit.agents import AgentFactory
from agent_toolkit.agents.specialists import techdocs_specialist  # noqa: F401 - registers tool
from agent_toolkit.application import ExecutionPipeline, ToolingBuilder
from agent_toolkit.config import AgentProfile, ConfigService, get_config_service
from agent_toolkit.config.swarm_presets import load_swarm_presets
from agent_toolkit.execution import ExecutionContext
from agent_toolkit.telemetry import setup_telemetry
from agent_toolkit.tools import DEFAULT_TOOL_REGISTRY, ToolCatalog
from agent_toolkit.tools.subagents import subagent  # noqa: F401 - registers tool

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from agent_toolkit.models.runtime import RuntimeAgent


def load_profiles(*_args, **_kwargs) -> dict[str, AgentProfile]:
    """Compatibility shim for tests that patch runtime.load_profiles."""
    return get_config_service().build_profiles()


class AgentRuntime:
    """Create and manage configured Strands agents."""

    def __init__(self) -> None:
        self._config_service: ConfigService = get_config_service()
        self._config_service.load_snapshot(force=True)
        self._settings = self._config_service.get_settings()
        self._tool_catalog = ToolCatalog(DEFAULT_TOOL_REGISTRY, self._config_service)
        self._tooling = ToolingBuilder(settings=self._settings, catalog=self._tool_catalog)
        self._factory = AgentFactory(settings=self._settings, registry=DEFAULT_TOOL_REGISTRY)
        self._swarm_presets = load_swarm_presets()
        self._swarm_preset = self._swarm_presets.get(self._settings.swarm_preset)
        self._pipeline = self._build_pipeline()

        self._telemetry_provider = setup_telemetry(self._settings)
        if self._telemetry_provider is not None:
            logger.info(
                "Phoenix telemetry initialized: endpoint=%s, project=%s",
                self._settings.phoenix_collector_endpoint,
                self._settings.phoenix_project_name,
            )

    def list_profiles(self) -> list[AgentProfile]:
        """List available agent profiles."""
        return list(self._config_service.build_profiles().values())

    def list_public_profiles(self) -> list[dict[str, Any]]:
        """List public profiles (visible to end users)."""
        public_profiles = self._config_service.list_public_profiles()
        return sorted(
            public_profiles.values(),
            key=lambda profile: (
                profile.get("metadata", {}).get("ui_order", 999),
                profile.get("id", ""),
            ),
        )

    def list_swarm_presets(self) -> list[str]:
        """List available swarm preset names."""
        return sorted(self._swarm_presets.keys())

    def set_swarm_preset(self, preset_name: str) -> None:
        """Select a swarm preset by name."""
        self._swarm_preset = self._swarm_presets.get(preset_name)
        self._pipeline = self._build_pipeline()

    def _build_pipeline(self) -> ExecutionPipeline:
        """Construct the execution pipeline with current settings."""
        return ExecutionPipeline(
            config_service=self._config_service,
            factory=self._factory,
            tooling=self._tooling,
            swarm_preset=self._swarm_preset,
        )

    def build_invocation_state(
        self,
        resource_uri: str,
        session_id: str,
        *,
        thread_id: str | None = None,
        message_id: str | None = None,
        run_mode: str | None = None,
        profile_name: str | None = None,
    ) -> dict[str, str]:
        """Build invocation state for multi-agent runs."""
        state: dict[str, str] = {}
        if resource_uri:
            state["resource_uri"] = resource_uri
        if session_id:
            state["session_id"] = session_id
        if thread_id:
            state["thread_id"] = thread_id
        if message_id:
            state["message_id"] = message_id
        if run_mode:
            state["run_mode"] = run_mode
        if profile_name:
            state["profile_name"] = profile_name
        return state

    def create_agent(
        self,
        profile_name: str,
        session_id: str = "",
        mode: str = "single",
        *,
        invocation_state: dict[str, str] | None = None,
        execution_mode: str = "",
        entrypoint_reference: str = "",
        model_override: str | None = None,
        tool_groups_override: list[str] | None = None,
    ) -> RuntimeAgent:
        """Create a runtime agent for a given profile."""
        return self._pipeline.create_agent(
            profile_name,
            session_id,
            mode=mode,
            invocation_state=invocation_state or {},
            execution_mode=execution_mode,
            entrypoint_reference=entrypoint_reference,
            model_override=model_override,
            tool_groups_override=tool_groups_override,
            profiles=load_profiles(),
        )

    def run(
        self,
        mode: str,
        profile_name: str,
        prompt: str,
        invocation_state: dict[str, str],
        session_id: str,
        *,
        model_override: str | None = None,
        tool_groups_override: list[str] | None = None,
    ) -> object:
        """Run a request based on the selected mode (sync, non-streaming)."""
        ctx = ExecutionContext(
            mode=mode,
            profile_name=profile_name,
            session_id=session_id,
            invocation_state=invocation_state,
            model_override=model_override,
            tool_groups_override=tool_groups_override,
        )
        return self._pipeline.run(ctx, prompt)

    async def stream(
        self,
        mode: str,
        profile_name: str,
        messages: list[dict[str, Any]],
        invocation_state: dict[str, str],
        session_id: str,
        *,
        model_override: str | None = None,
        tool_groups_override: list[str] | None = None,
    ):
        """Stream a request based on the selected mode."""
        ctx = ExecutionContext(
            mode=mode,
            profile_name=profile_name,
            session_id=session_id,
            invocation_state=invocation_state,
            model_override=model_override,
            tool_groups_override=tool_groups_override,
        )
        async for event in self._pipeline.stream(ctx, messages):
            yield event


__all__ = ["AgentRuntime"]
