"""Execution strategies and context for agent runtime.

This module implements the Strategy pattern for different execution modes:
- SingleAgentStrategy: Direct agent invocation with history injection
- SwarmStrategy: Multi-agent swarm orchestration
- GraphStrategy: Graph-based workflow execution

Each strategy encapsulates mode-specific streaming logic while the AgentRuntime
handles telemetry, snapshots, and lifecycle concerns (Single Responsibility).

Reference: 12-Factor Agents - Factor 8 (Own Your Control Flow)
Reference: 12-Factor Agents - Factor 10 (Small, Focused Agents)

Design Principles:
1. Strategies yield raw Strands events, leaving telemetry to the caller
2. OutputAccumulator is passed in for caller to track output/tool events
3. Message history injection happens at strategy level for single agent
4. All strategies have consistent async stream() interface
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from strands import Agent

    from agent_toolkit.stream_utils import OutputAccumulator

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context for agent execution, reducing parameter passing."""

    mode: str  # selected public profile name (run mode)
    profile_name: str
    session_id: str
    invocation_state: dict[str, str] = field(default_factory=dict)
    # New fields for resolved execution metadata
    resolved_metadata: dict[str, Any] = field(default_factory=dict)
    resolved_execution_mode: str = ""
    resolved_entrypoint: str = ""
    model_override: str | None = None
    tool_groups_override: list[str] | None = None

    @property
    def resource_uri(self) -> str:
        """Get resource URI from invocation state."""
        return self.invocation_state.get("resource_uri", "")

    def effective_session_id(self) -> str:
        """Get session ID or generate default from mode/profile."""
        return self.session_id or f"{self.mode}-{self.profile_name}"


@dataclass
class ExecutionResult:
    """Result of an execution strategy run."""

    output: str
    tool_events: list[dict[str, str]]
    trace_id: str | None = None
    metrics: dict | None = None


class ExecutionStrategy(ABC):
    """Base class for execution strategies.

    Each strategy handles a specific execution mode (single, swarm, graph).
    Strategies yield raw Strands events - telemetry and snapshots are
    handled by the caller (AgentRuntime).

    Implementations must:
    1. Yield dict events conforming to Strands streaming protocol
    2. Call accumulator.process_event() for each event
    3. Pass invocation_state to multi-agent systems if provided
    """

    @abstractmethod
    async def stream(
        self,
        prompt: str,
        accumulator: OutputAccumulator,
        invocation_state: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream events from execution.

        Args:
            prompt: User prompt or formatted input to execute.
            accumulator: Shared accumulator for output and tool tracking.
            invocation_state: Optional state to pass to multi-agent systems.

        Yields:
            Dict events conforming to the Strands streaming protocol.
        """
        yield {}  # pragma: no cover


class SingleAgentStrategy(ExecutionStrategy):
    """Execute with a single agent.

    Handles message history injection for conversation continuity.
    """

    def __init__(self, agent: Agent, history_messages: list[dict[str, Any]] | None = None) -> None:
        """Initialize with agent and optional conversation history.

        Args:
            agent: The Strands agent to execute.
            history_messages: Previous messages to inject for context.
        """
        self._agent = agent
        self._history = history_messages or []

    async def stream(
        self,
        prompt: str,
        accumulator: OutputAccumulator,
        invocation_state: dict[str, str] | None = None,  # noqa: ARG002 - interface consistency
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream from single agent execution."""
        # Inject history messages for conversation context
        if self._history:
            self._agent.messages.extend(self._history)
            logger.info("Injected %d history messages into agent", len(self._history))

        async for event in self._agent.stream_async(prompt):
            accumulator.process_event(event)
            yield event


class SwarmStrategy(ExecutionStrategy):
    """Execute with a swarm of agents."""

    def __init__(self, swarm: Any) -> None:
        self._swarm = swarm

    async def stream(
        self,
        prompt: str,
        accumulator: OutputAccumulator,
        invocation_state: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream from swarm execution."""
        if not hasattr(self._swarm, "stream_async"):
            logger.warning("Swarm does not support stream_async")
            return

        async for event in self._swarm.stream_async(
            prompt, invocation_state=invocation_state or {}
        ):
            accumulator.process_event(event)
            yield event


class GraphStrategy(ExecutionStrategy):
    """Execute with a graph-based workflow."""

    def __init__(self, graph: Any) -> None:
        self._graph = graph

    async def stream(
        self,
        prompt: str,
        accumulator: OutputAccumulator,
        invocation_state: dict[str, str] | None = None,
    ) -> AsyncIterator[dict[str, Any]]:
        """Stream from graph execution."""
        if hasattr(self._graph, "stream_async"):
            async for event in self._graph.stream_async(
                prompt, invocation_state=invocation_state or {}
            ):
                accumulator.process_event(event)
                yield event
            return

        # Non-streaming fallback
        result = await self._graph.invoke_async(prompt, invocation_state=invocation_state or {})
        output = str(result)
        accumulator.output_buffer.append(output)
        yield {"data": output, "complete": True}
