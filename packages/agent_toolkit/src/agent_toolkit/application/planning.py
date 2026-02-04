"""Execution planning helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_toolkit.config import ConfigService


@dataclass(frozen=True)
class ExecutionPlan:
    """Resolved execution plan for a run."""

    execution_mode: str
    entrypoint_reference: str
    metadata: dict[str, Any]


def resolve_execution_plan(config_service: ConfigService, profile_name: str) -> ExecutionPlan:
    """Resolve profile to execution mode and entrypoint."""
    execution_mode, entrypoint_reference, metadata = config_service.resolve_execution_mode(
        profile_name
    )
    return ExecutionPlan(
        execution_mode=execution_mode,
        entrypoint_reference=entrypoint_reference,
        metadata=metadata,
    )
