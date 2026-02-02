"""Telemetry package for agent observability.

This package provides telemetry and observability integrations,
including Phoenix for LLM trace visualization and analysis.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from agent_toolkit.telemetry.evaluator import (
    EvalConfig,
    EvalResult,
    OnlineEvaluator,
    get_online_evaluator,
    reset_evaluator,
)
from agent_toolkit.telemetry.phoenix import (
    PhoenixConfig,
    PhoenixTelemetryProvider,
    SessionTurnContext,
    get_current_trace_id,
)

if TYPE_CHECKING:
    from agent_toolkit.config.settings import Settings

__all__ = [
    "EvalConfig",
    "EvalResult",
    "OnlineEvaluator",
    "PhoenixConfig",
    "PhoenixTelemetryProvider",
    "SessionTurnContext",
    "build_trace_attributes",
    "get_current_trace_id",
    "get_online_evaluator",
    "get_telemetry_provider",
    "reset_evaluator",
    "setup_telemetry",
    "shutdown_telemetry",
]

logger = logging.getLogger(__name__)

# Global telemetry provider instance (singleton pattern)
_telemetry_provider: PhoenixTelemetryProvider | None = None


def setup_telemetry(settings: Settings) -> PhoenixTelemetryProvider | None:
    """Set up telemetry from application settings.

    This function initializes the Phoenix telemetry provider based on
    the provided settings. It uses a singleton pattern to ensure only
    one provider is created per process.

    Args:
        settings: Application settings containing Phoenix configuration.

    Returns:
        The initialized PhoenixTelemetryProvider, or None if disabled.
    """
    global _telemetry_provider  # noqa: PLW0603

    if _telemetry_provider is not None:
        logger.debug("Telemetry already initialized, returning existing provider")
        return _telemetry_provider

    config = PhoenixConfig.from_settings(settings)
    provider = PhoenixTelemetryProvider(config)

    if provider.setup() is not None:
        _telemetry_provider = provider
        return provider

    return None


def get_telemetry_provider() -> PhoenixTelemetryProvider | None:
    """Get the global telemetry provider instance.

    Returns:
        The global PhoenixTelemetryProvider, or None if not initialized.
    """
    return _telemetry_provider


def shutdown_telemetry() -> None:
    """Shut down the global telemetry provider."""
    global _telemetry_provider  # noqa: PLW0603

    if _telemetry_provider is not None:
        _telemetry_provider.shutdown()
        _telemetry_provider = None


def build_trace_attributes(
    *,
    session_id: str = "",
    profile_name: str = "",
    run_mode: str = "",
    thread_id: str = "",
    message_id: str = "",
    execution_mode: str = "",
    entrypoint_reference: str = "",
    **extra: Any,
) -> dict[str, str]:
    """Build trace attributes for agent context.

    Convenience function that delegates to the telemetry provider.

    Args:
        session_id: Session identifier.
        profile_name: Agent profile name.
        run_mode: Public run mode/profile identifier.
        thread_id: Thread identifier for UI correlation.
        message_id: Message identifier for UI correlation.
        execution_mode: Resolved execution mode (single, graph, swarm).
        entrypoint_reference: Reference to the actual entrypoint being executed.
        **extra: Additional custom attributes.

    Returns:
        Dictionary of trace attributes.
    """
    if _telemetry_provider is not None:
        return _telemetry_provider.build_trace_attributes(
            session_id=session_id,
            profile_name=profile_name,
            run_mode=run_mode,
            thread_id=thread_id,
            message_id=message_id,
            execution_mode=execution_mode,
            entrypoint_reference=entrypoint_reference,
            **extra,
        )
    # Return basic attributes even without provider
    attrs: dict[str, str] = {}
    if session_id:
        attrs["session.id"] = session_id
    if profile_name:
        attrs["agent.profile"] = profile_name
    if run_mode:
        attrs["run.mode"] = run_mode
    if thread_id:
        attrs["thread.id"] = thread_id
    if message_id:
        attrs["message.id"] = message_id
    if execution_mode:
        attrs["run.execution_mode"] = execution_mode
    if entrypoint_reference:
        attrs["run.entrypoint"] = entrypoint_reference
    for key, value in extra.items():
        attrs[key] = str(value)
    return attrs
