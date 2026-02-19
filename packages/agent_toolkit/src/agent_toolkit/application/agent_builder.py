"""Runtime agent construction helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_toolkit.hooks import (
    PlanModeHook,
    TechDocsWorkflowHook,
    ToolApprovalHook,
    ToolTelemetry,
    ToolTelemetryHook,
)
from agent_toolkit.mcp.client_resolver import get_mcp_clients_for_profile
from agent_toolkit.models.runtime import RuntimeAgent
from agent_toolkit.plan_mode import PlanModeSettings
from agent_toolkit.telemetry import build_trace_attributes

if TYPE_CHECKING:
    from agent_toolkit.agents import AgentFactory


def build_runtime_agent(
    *,
    config_service: Any,
    factory: AgentFactory,
    tooling: Any,
    profile_name: str,
    session_id: str,
    mode: str,
    invocation_state: dict[str, str],
    execution_mode: str,
    entrypoint_reference: str,
    profiles: dict[str, Any] | None = None,
) -> RuntimeAgent:
    """Build a runtime agent with telemetry hooks."""
    resolved_profiles = profiles or config_service.build_profiles()
    profile = resolved_profiles.get(profile_name)
    if profile is None:
        msg = f"Unknown agent profile: {profile_name}"
        raise ValueError(msg)

    profile = tooling.apply_profile_overrides(profile)

    telemetry = ToolTelemetry()
    hooks = [ToolTelemetryHook(telemetry)]
    plan_mode = PlanModeSettings.from_metadata(profile.metadata)
    if plan_mode.enabled:
        hooks.append(PlanModeHook(plan_mode))

    if tooling.settings.approval_tools:
        hooks.append(ToolApprovalHook(tooling.settings.approval_tools))

    if "techdocs" in profile.tool_groups:
        hooks.append(TechDocsWorkflowHook())

    trace_state = invocation_state or {}
    thread_id = trace_state.get("thread_id", "")
    message_id = trace_state.get("message_id", "")
    run_mode = trace_state.get("run_mode", mode)

    trace_attrs = build_trace_attributes(
        session_id=session_id,
        profile_name=profile_name,
        run_mode=run_mode,
        thread_id=thread_id,
        message_id=message_id,
        execution_mode=execution_mode,
        entrypoint_reference=entrypoint_reference,
    )

    mcp_clients = get_mcp_clients_for_profile(profile)

    agent = factory.create_from_profile(
        profile,
        session_id=session_id,
        hooks=hooks,
        trace_attributes=trace_attrs or None,
        mcp_clients=mcp_clients or None,
    )
    return RuntimeAgent(profile=profile, agent=agent, telemetry=telemetry)
