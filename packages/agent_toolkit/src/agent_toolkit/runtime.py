"""Agent runtime orchestration layer.

This module provides the main AgentRuntime class that orchestrates agent creation,
execution, and lifecycle management. It's the primary entry point for running
agents in the playground.

Architecture:
- AgentRuntime: Facade that coordinates profiles, factories, and execution
- RuntimeAgent: Container pairing an agent with its telemetry state
- Execution uses Strategy pattern (see execution.py) for mode-specific logic

12-Factor Agents References:
- Factor 8: Own Your Control Flow (runtime manages the agent loop)
- Factor 9: Compact Logs, Rich Telemetry (snapshots capture run history)
- Factor 10: Small, Focused Agents (profiles define focused agent configs)
"""

from __future__ import annotations

import logging
from typing import Any

from agent_toolkit.agents import AgentFactory, build_session_manager
from agent_toolkit.agents.specialists import techdocs_specialist  # noqa: F401 - registers tool
from agent_toolkit.config import (
    AgentProfile,
    load_profiles,
    load_settings,
)
from agent_toolkit.config.execution_mode import get_execution_mode_resolver
from agent_toolkit.config.new_loader import NewConfigLoader
from agent_toolkit.config.swarm_presets import load_swarm_presets
from agent_toolkit.execution import (
    ExecutionContext,
    GraphStrategy,
    SingleAgentStrategy,
    SwarmStrategy,
)
from agent_toolkit.hooks import (
    PlanModeHook,
    TechDocsWorkflowHook,
    ToolApprovalHook,
    ToolTelemetry,
    ToolTelemetryHook,
)
from agent_toolkit.mcp.client_resolver import get_mcp_clients_for_profile
from agent_toolkit.metrics import extract_metrics_from_event
from agent_toolkit.models.runtime import RuntimeAgent
from agent_toolkit.multiagent import build_graph, build_swarm
from agent_toolkit.plan_mode import PlanModeSettings
from agent_toolkit.run_history import new_run_id
from agent_toolkit.snapshot_recorder import (
    build_tool_events_from_telemetry,
    record_run_snapshot,
)
from agent_toolkit.stream_utils import (
    OutputAccumulator,
    build_multiagent_prompt,
    create_metadata_event,
    extract_prompt_for_log,
    split_messages_for_single_mode,
)
from agent_toolkit.telemetry import SessionTurnContext, build_trace_attributes, setup_telemetry
from agent_toolkit.tools import DEFAULT_TOOL_REGISTRY
from agent_toolkit.tools.subagents import subagent  # noqa: F401 - registers tool
from agent_toolkit.utils import utc_timestamp

logger = logging.getLogger(__name__)


class AgentRuntime:
    """Create and manage configured Strands agents."""

    def __init__(self) -> None:
        """Load profiles and settings for runtime usage."""
        self._settings = load_settings()
        self._profiles = load_profiles(registry=DEFAULT_TOOL_REGISTRY)
        self._factory = AgentFactory(settings=self._settings, registry=DEFAULT_TOOL_REGISTRY)
        self._swarm_presets = load_swarm_presets()
        self._swarm_preset = self._swarm_presets.get(self._settings.swarm_preset)

        # Initialize execution mode resolver for new config schema
        self._mode_resolver = get_execution_mode_resolver(DEFAULT_TOOL_REGISTRY)

        # Initialize Phoenix telemetry if enabled
        self._telemetry_provider = setup_telemetry(self._settings)
        if self._telemetry_provider is not None:
            logger.info(
                "Phoenix telemetry initialized: endpoint=%s, project=%s",
                self._settings.phoenix_collector_endpoint,
                self._settings.phoenix_project_name,
            )

    def list_profiles(self) -> list[AgentProfile]:
        """List available agent profiles."""
        return list(self._profiles.values())

    def list_public_profiles(self) -> list[dict[str, Any]]:
        """List public profiles (visible to end users)."""
        public_profiles = self._mode_resolver.get_public_profiles()
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
        profile = self._profiles.get(profile_name)
        if profile is None:
            message = f"Unknown agent profile: {profile_name}"
            raise ValueError(message)
        profile = self._apply_profile_overrides(profile, model_override, tool_groups_override)

        telemetry = ToolTelemetry()
        hooks = [ToolTelemetryHook(telemetry)]
        plan_mode = PlanModeSettings.from_metadata(profile.metadata)
        if plan_mode.enabled:
            hooks.append(PlanModeHook(plan_mode))

        if self._settings.approval_tools:
            hooks.append(ToolApprovalHook(self._settings.approval_tools))

        # Add TechDocs workflow enforcement for profiles using techdocs tools
        if "techdocs" in profile.tool_groups:
            hooks.append(TechDocsWorkflowHook())

        trace_state = invocation_state or {}
        thread_id = trace_state.get("thread_id", "")
        message_id = trace_state.get("message_id", "")
        run_mode = trace_state.get("run_mode", mode)

        # Build trace attributes for Phoenix telemetry
        trace_attrs = build_trace_attributes(
            session_id=session_id,
            profile_name=profile_name,
            run_mode=run_mode,
            thread_id=thread_id,
            message_id=message_id,
            execution_mode=execution_mode,
            entrypoint_reference=entrypoint_reference,
        )

        # Get MCP clients for this profile based on tool_group capabilities
        mcp_clients = get_mcp_clients_for_profile(profile)

        agent = self._factory.create_from_profile(
            profile,
            session_id=session_id,
            hooks=hooks,
            trace_attributes=trace_attrs or None,
            mcp_clients=mcp_clients if mcp_clients else None,
        )
        return RuntimeAgent(profile=profile, agent=agent, telemetry=telemetry)

    def _apply_profile_overrides(
        self,
        profile: AgentProfile,
        model_override: str | None,
        tool_groups_override: list[str] | None,
    ) -> AgentProfile:
        if not model_override and tool_groups_override is None:
            return profile

        updates: dict[str, Any] = {}
        if model_override:
            updates["model"] = model_override

        if tool_groups_override is not None:
            tools = self._build_tools_for_profile(profile.name, tool_groups_override)
            updates["tools"] = tools
            updates["tool_groups"] = list(tool_groups_override)

        if not updates:
            return profile

        return profile.model_copy(update=updates)

    def apply_profile_overrides(
        self,
        profile: AgentProfile,
        model_override: str | None,
        tool_groups_override: list[str] | None,
    ) -> AgentProfile:
        """Return a copy of the profile with overrides applied."""
        return self._apply_profile_overrides(profile, model_override, tool_groups_override)

    def _build_tools_for_profile(self, profile_name: str, tool_groups: list[str]) -> list[str]:
        loader = NewConfigLoader()
        schema, validation = loader.load()
        if not validation.valid:
            msg = f"Configuration validation failed: {validation.errors}"
            raise ValueError(msg)

        agent = schema.agents.get(profile_name)
        if not agent:
            return []

        all_tools = list(agent.tools)
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
        run_id = new_run_id()
        started_at = utc_timestamp()
        tool_events: list[dict[str, str]] = []
        session_manager = build_session_manager(self._settings, ctx.effective_session_id())

        execution_mode, entrypoint_reference, metadata = self._mode_resolver.resolve_execution_mode(
            ctx.profile_name
        )
        ctx.resolved_metadata = metadata
        ctx.resolved_execution_mode = execution_mode
        ctx.resolved_entrypoint = entrypoint_reference

        thread_id = ctx.invocation_state.get("thread_id", "")
        message_id = ctx.invocation_state.get("message_id", "")
        trace_attrs = build_trace_attributes(
            session_id=ctx.session_id,
            profile_name=ctx.profile_name,
            run_mode=ctx.mode,
            thread_id=thread_id,
            message_id=message_id,
            execution_mode=execution_mode,
            entrypoint_reference=entrypoint_reference,
        )

        if execution_mode == "graph":
            graph: Any = build_graph(
                self._settings,
                session_manager=session_manager,
                template_name=entrypoint_reference,
                trace_attributes=trace_attrs,
            )
            result = graph(prompt, invocation_state=ctx.invocation_state)
        elif execution_mode == "swarm":
            swarm: Any = build_swarm(
                self._settings,
                session_manager=session_manager,
                preset=self._swarm_preset,
                template_name=entrypoint_reference,
                trace_attributes=trace_attrs,
            )
            result = swarm(prompt, invocation_state=ctx.invocation_state)
        else:
            runtime_agent = self.create_agent(
                entrypoint_reference,
                ctx.session_id,
                mode=ctx.mode,
                invocation_state=ctx.invocation_state,
                execution_mode=execution_mode,
                entrypoint_reference=entrypoint_reference,
                model_override=ctx.model_override,
                tool_groups_override=ctx.tool_groups_override,
            )
            result = runtime_agent.agent(prompt)
            tool_events = build_tool_events_from_telemetry(runtime_agent.telemetry)

        record_run_snapshot(
            run_id=run_id,
            mode=ctx.resolved_execution_mode or execution_mode,
            profile=ctx.profile_name,
            session_id=ctx.session_id,
            resource_uri=ctx.resource_uri,
            prompt=prompt,
            output=str(result),
            tool_events=tool_events,
            started_at=started_at,
        )
        return result

    async def stream(  # noqa: C901, PLR0912
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
        """Stream a request based on the selected mode.

        Uses the Strategy pattern for mode-specific execution while keeping
        telemetry and snapshot recording in one place (Single Responsibility).

        Args:
            mode: Execution mode (single, graph, swarm)
            profile_name: Name of the agent profile to use
            messages: Full conversation history in Strands message format
            invocation_state: State to pass to the agent
            session_id: Session ID for persistence
            model_override: Optional model override for this run.
            tool_groups_override: Optional tool group override for this run.
        """
        ctx = ExecutionContext(
            mode=mode,
            profile_name=profile_name,
            session_id=session_id,
            invocation_state=invocation_state,
            model_override=model_override,
            tool_groups_override=tool_groups_override,
        )
        run_id = new_run_id()
        started_at = utc_timestamp()
        accumulator = OutputAccumulator()
        captured_metrics: dict | None = None
        prompt_for_log = extract_prompt_for_log(messages)

        # Build the appropriate strategy (this populates resolved fields in ctx)
        strategy = self._build_strategy(ctx, messages)

        # Get prompt based on resolved execution mode
        if ctx.resolved_execution_mode == "single":
            prompt, _ = split_messages_for_single_mode(messages)
        else:
            prompt = build_multiagent_prompt(messages)

        # Create telemetry context for Phoenix tracing with resolved metadata
        turn_ctx = SessionTurnContext(
            session_id=ctx.session_id,
            run_mode=ctx.mode,
            input_value=prompt,
            profile_name=ctx.profile_name,
            thread_id=ctx.invocation_state.get("thread_id"),
            message_id=ctx.invocation_state.get("message_id"),
            execution_mode=ctx.resolved_execution_mode or "",
            entrypoint_reference=ctx.resolved_entrypoint or "",
        )

        # Stream with telemetry wrapper
        try:
            with turn_ctx.span():
                async for event in strategy.stream(prompt, accumulator, ctx.invocation_state):
                    metrics = extract_metrics_from_event(event)
                    if metrics is not None:
                        captured_metrics = metrics.to_dict()

                    if isinstance(event, dict):
                        event_type = event.get("type")
                        if event_type in (
                            "multiagent_node_start",
                            "multiagent_node_stop",
                            "multiagent_handoff",
                        ):
                            attrs: dict[str, Any] = {"event_type": event_type}
                            if event.get("node_id"):
                                attrs["node_id"] = event.get("node_id")
                            if event_type == "multiagent_handoff":
                                attrs["from_node_ids"] = event.get("from_node_ids", [])
                                attrs["to_node_ids"] = event.get("to_node_ids", [])
                                if event.get("message"):
                                    attrs["handoff_message"] = event.get("message")
                            turn_ctx.add_event(f"multiagent.{event_type}", attrs)

                    # Add Phoenix metadata to every event if available
                    if turn_ctx.trace_id and isinstance(event, dict):
                        event["phoenix_trace_id"] = turn_ctx.trace_id
                        if ctx.session_id:
                            event["phoenix_session_id"] = ctx.session_id

                    yield event
                turn_ctx.set_output(accumulator.get_output())

            # Emit final metadata event for stream consumers
            if turn_ctx.trace_id:
                yield create_metadata_event(turn_ctx.trace_id, ctx.session_id)

        except Exception:
            logger.exception("Error during stream execution for session %s", ctx.session_id)
            yield {"error": "Stream execution failed", "complete": True}

        # Write snapshot after streaming completes
        record_run_snapshot(
            run_id=run_id,
            mode=ctx.resolved_execution_mode or ctx.mode,  # Use resolved mode
            profile=ctx.profile_name,
            session_id=ctx.session_id,
            resource_uri=ctx.resource_uri,
            prompt=prompt_for_log,
            output=accumulator.get_output(),
            tool_events=accumulator.tool_events,
            started_at=started_at,
            metrics=captured_metrics,
        )

    def _build_strategy(
        self,
        ctx: ExecutionContext,
        messages: list[dict[str, Any]],
    ):
        """Build execution strategy for the given mode.

        Factory method that encapsulates strategy construction.
        Uses public profile configuration to determine execution mode and entrypoint.
        """
        # Resolve execution mode from profile configuration
        execution_mode, entrypoint_reference, metadata = self._mode_resolver.resolve_execution_mode(
            ctx.profile_name
        )
        logger.info(
            "Resolved profile '%s' to execution_mode='%s', entrypoint='%s'",
            ctx.profile_name,
            execution_mode,
            entrypoint_reference,
        )

        # Store resolved metadata in context for later use
        ctx.resolved_metadata = metadata
        ctx.resolved_execution_mode = execution_mode
        ctx.resolved_entrypoint = entrypoint_reference

        thread_id = ctx.invocation_state.get("thread_id", "")
        message_id = ctx.invocation_state.get("message_id", "")
        trace_attrs = build_trace_attributes(
            session_id=ctx.session_id,
            profile_name=ctx.profile_name,
            run_mode=ctx.mode,
            thread_id=thread_id,
            message_id=message_id,
            execution_mode=execution_mode,
            entrypoint_reference=entrypoint_reference,
        )

        if execution_mode == "swarm":
            logger.info("Building swarm with template: %s", entrypoint_reference)
            if ctx.model_override or ctx.tool_groups_override is not None:
                logger.warning("Model/tool overrides are not applied to swarm executions")
            swarm = build_swarm(
                self._settings,
                session_manager=None,
                preset=self._swarm_preset,
                template_name=entrypoint_reference,
                trace_attributes=trace_attrs,
            )
            return SwarmStrategy(swarm)

        if execution_mode == "graph":
            logger.info("Building graph with template: %s", entrypoint_reference)
            if ctx.model_override or ctx.tool_groups_override is not None:
                logger.warning("Model/tool overrides are not applied to graph executions")
            graph = build_graph(
                self._settings,
                session_manager=None,
                template_name=entrypoint_reference,
                trace_attributes=trace_attrs,
            )
            return GraphStrategy(graph)

        # Single agent mode - includes history injection
        _, history_messages = split_messages_for_single_mode(messages)
        # Use resolved entrypoint as profile name
        profile_name = entrypoint_reference
        runtime_agent = self.create_agent(
            profile_name,
            ctx.session_id,
            mode=ctx.mode,
            invocation_state=ctx.invocation_state,
            execution_mode=execution_mode,
            entrypoint_reference=entrypoint_reference,
            model_override=ctx.model_override,
            tool_groups_override=ctx.tool_groups_override,
        )
        return SingleAgentStrategy(runtime_agent.agent, history_messages)
