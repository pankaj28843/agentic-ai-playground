"""Execution pipeline for agent runs."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agent_toolkit.agents import AgentFactory, build_session_manager
from agent_toolkit.application.agent_builder import build_runtime_agent
from agent_toolkit.application.planning import ExecutionPlan, resolve_execution_plan
from agent_toolkit.compaction import StreamCompactionPolicy
from agent_toolkit.execution import (
    ExecutionContext,
    GraphStrategy,
    SingleAgentStrategy,
    SwarmStrategy,
)
from agent_toolkit.metrics import extract_metrics_from_event
from agent_toolkit.multiagent import build_graph, build_swarm
from agent_toolkit.run_history import new_run_id
from agent_toolkit.snapshot_recorder import build_tool_events_from_telemetry, record_run_snapshot
from agent_toolkit.stream_utils import (
    OutputAccumulator,
    build_multiagent_prompt,
    create_metadata_event,
    extract_prompt_for_log,
    split_messages_for_single_mode,
)
from agent_toolkit.telemetry import SessionTurnContext, build_trace_attributes
from agent_toolkit.utils import utc_timestamp

if TYPE_CHECKING:
    from agent_toolkit.application.tooling import ToolingBuilder
    from agent_toolkit.config import ConfigService
    from agent_toolkit.config.swarm_presets import SwarmPreset
    from agent_toolkit.models.runtime import RuntimeAgent

logger = logging.getLogger(__name__)


class ExecutionPipeline:
    """Orchestrate agent execution with minimal runtime wiring."""

    def __init__(
        self,
        *,
        config_service: ConfigService,
        factory: AgentFactory,
        tooling: ToolingBuilder,
        swarm_preset: SwarmPreset | None,
    ) -> None:
        self._config_service = config_service
        self._factory = factory
        self._tooling = tooling
        self._swarm_preset = swarm_preset
        self._stream_compaction = StreamCompactionPolicy.from_settings(tooling.settings)

    def resolve_plan(self, profile_name: str) -> ExecutionPlan:
        """Resolve profile to execution mode and entrypoint."""
        return resolve_execution_plan(self._config_service, profile_name)

    def create_agent(
        self,
        profile_name: str,
        session_id: str,
        *,
        mode: str,
        invocation_state: dict[str, str],
        execution_mode: str,
        entrypoint_reference: str,
        model_override: str | None,
        tool_groups_override: list[str] | None,
        profiles: dict[str, Any] | None = None,
    ) -> RuntimeAgent:
        """Build a runtime agent with telemetry hooks."""
        return build_runtime_agent(
            config_service=self._config_service,
            factory=self._factory,
            tooling=self._tooling,
            profile_name=profile_name,
            session_id=session_id,
            mode=mode,
            invocation_state=invocation_state,
            execution_mode=execution_mode,
            entrypoint_reference=entrypoint_reference,
            model_override=model_override,
            tool_groups_override=tool_groups_override,
            profiles=profiles,
        )

    def run(
        self,
        ctx: ExecutionContext,
        prompt: str,
    ) -> object:
        """Run a non-streaming execution path."""
        run_id = new_run_id()
        started_at = utc_timestamp()
        tool_events: list[dict[str, str]] = []
        session_manager = build_session_manager(self._tooling.settings, ctx.effective_session_id())

        plan = self.resolve_plan(ctx.profile_name)
        ctx.resolved_metadata = plan.metadata
        ctx.resolved_execution_mode = plan.execution_mode
        ctx.resolved_entrypoint = plan.entrypoint_reference

        thread_id = ctx.invocation_state.get("thread_id", "")
        message_id = ctx.invocation_state.get("message_id", "")
        trace_attrs = build_trace_attributes(
            session_id=ctx.session_id,
            profile_name=ctx.profile_name,
            run_mode=ctx.mode,
            thread_id=thread_id,
            message_id=message_id,
            execution_mode=plan.execution_mode,
            entrypoint_reference=plan.entrypoint_reference,
        )

        if plan.execution_mode == "graph":
            graph: Any = build_graph(
                self._tooling.settings,
                session_manager=session_manager,
                template_name=plan.entrypoint_reference,
                trace_attributes=trace_attrs,
                model_override=ctx.model_override,
                tool_groups_override=ctx.tool_groups_override,
            )
            result = graph(prompt, invocation_state=ctx.invocation_state)
        elif plan.execution_mode == "swarm":
            swarm: Any = build_swarm(
                self._tooling.settings,
                session_manager=session_manager,
                preset=self._swarm_preset,
                template_name=plan.entrypoint_reference,
                trace_attributes=trace_attrs,
                model_override=ctx.model_override,
                tool_groups_override=ctx.tool_groups_override,
            )
            result = swarm(prompt, invocation_state=ctx.invocation_state)
        else:
            runtime_agent = self.create_agent(
                plan.entrypoint_reference,
                ctx.session_id,
                mode=ctx.mode,
                invocation_state=ctx.invocation_state,
                execution_mode=plan.execution_mode,
                entrypoint_reference=plan.entrypoint_reference,
                model_override=ctx.model_override,
                tool_groups_override=ctx.tool_groups_override,
            )
            result = runtime_agent.agent(prompt)
            tool_events = build_tool_events_from_telemetry(runtime_agent.telemetry)

        record_run_snapshot(
            run_id=run_id,
            mode=plan.execution_mode,
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
        ctx: ExecutionContext,
        messages: list[dict[str, Any]],
    ):
        """Stream a request based on resolved execution mode."""
        run_id = new_run_id()
        started_at = utc_timestamp()
        accumulator = OutputAccumulator()
        captured_metrics: dict | None = None
        prompt_for_log = extract_prompt_for_log(messages)

        strategy = self._build_strategy(ctx, messages)
        messages_for_prompt = messages
        if (
            self._stream_compaction.enabled
            and ctx.resolved_execution_mode
            and ctx.resolved_execution_mode != "single"
        ):
            decision = self._stream_compaction.apply(messages)
            messages_for_prompt = decision.kept_messages
            if decision.dropped_messages:
                logger.info(
                    "Stream compaction trimmed %d messages (kept=%d tokens_before=%d)",
                    len(decision.dropped_messages),
                    len(decision.kept_messages),
                    decision.tokens_before,
                )

        if ctx.resolved_execution_mode == "single":
            prompt, _ = split_messages_for_single_mode(messages)
        else:
            prompt = build_multiagent_prompt(messages_for_prompt)

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

                    if turn_ctx.trace_id and isinstance(event, dict):
                        event["phoenix_trace_id"] = turn_ctx.trace_id
                        if ctx.session_id:
                            event["phoenix_session_id"] = ctx.session_id

                    yield event
                turn_ctx.set_output(accumulator.get_output())

            if turn_ctx.trace_id:
                yield create_metadata_event(turn_ctx.trace_id, ctx.session_id)

        except Exception:
            logger.exception("Error during stream execution for session %s", ctx.session_id)
            yield {"error": "Stream execution failed", "complete": True}

        record_run_snapshot(
            run_id=run_id,
            mode=ctx.resolved_execution_mode or ctx.mode,
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
        plan = self.resolve_plan(ctx.profile_name)
        logger.info(
            "Resolved profile '%s' to execution_mode='%s', entrypoint='%s'",
            ctx.profile_name,
            plan.execution_mode,
            plan.entrypoint_reference,
        )

        ctx.resolved_metadata = plan.metadata
        ctx.resolved_execution_mode = plan.execution_mode
        ctx.resolved_entrypoint = plan.entrypoint_reference

        thread_id = ctx.invocation_state.get("thread_id", "")
        message_id = ctx.invocation_state.get("message_id", "")
        trace_attrs = build_trace_attributes(
            session_id=ctx.session_id,
            profile_name=ctx.profile_name,
            run_mode=ctx.mode,
            thread_id=thread_id,
            message_id=message_id,
            execution_mode=plan.execution_mode,
            entrypoint_reference=plan.entrypoint_reference,
        )

        if plan.execution_mode == "swarm":
            swarm = build_swarm(
                self._tooling.settings,
                session_manager=None,
                preset=self._swarm_preset,
                template_name=plan.entrypoint_reference,
                trace_attributes=trace_attrs,
                model_override=ctx.model_override,
                tool_groups_override=ctx.tool_groups_override,
            )
            return SwarmStrategy(swarm)

        if plan.execution_mode == "graph":
            graph = build_graph(
                self._tooling.settings,
                session_manager=None,
                template_name=plan.entrypoint_reference,
                trace_attributes=trace_attrs,
                model_override=ctx.model_override,
                tool_groups_override=ctx.tool_groups_override,
            )
            return GraphStrategy(graph)

        _, history_messages = split_messages_for_single_mode(messages)
        runtime_agent = self.create_agent(
            plan.entrypoint_reference,
            ctx.session_id,
            mode=ctx.mode,
            invocation_state=ctx.invocation_state,
            execution_mode=plan.execution_mode,
            entrypoint_reference=plan.entrypoint_reference,
            model_override=ctx.model_override,
            tool_groups_override=ctx.tool_groups_override,
        )
        return SingleAgentStrategy(runtime_agent.agent, history_messages)
