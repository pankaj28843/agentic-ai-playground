"""Pydantic models for runtime components."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class RuntimeAgent(BaseModel):
    """Container for an active agent and its telemetry state.

    Bundles the agent instance with its profile and telemetry tracker
    so callers have everything needed for invocation and introspection.
    """

    profile: Any  # AgentProfile - use Any to avoid circular import at runtime
    agent: Any  # strands.Agent - not a Pydantic model
    telemetry: Any  # ToolTelemetry - not a Pydantic model

    model_config = ConfigDict(arbitrary_types_allowed=True)
