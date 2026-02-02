"""Agent loop metrics capture and formatting.

This module provides dataclasses for capturing and normalizing metrics from
Strands agent runs, inspired by the Codex CLI agent loop architecture.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from strands.agent.agent_result import AgentResult


@dataclass(frozen=True)
class AgentLoopMetrics:
    """Normalized metrics from a Strands agent run.

    Captures key performance indicators from the EventLoopMetrics
    provided by Strands after each agent invocation.
    """

    total_cycles: int
    """Number of agent loop iterations (inference + tool calls)."""

    total_duration_ms: float
    """Total execution time in milliseconds."""

    input_tokens: int
    """Total input tokens consumed."""

    output_tokens: int
    """Total output tokens generated."""

    total_tokens: int
    """Sum of input and output tokens."""

    stop_reason: str
    """Reason the agent loop terminated (end_turn, max_tokens, etc.)."""

    tool_stats: dict[str, dict[str, Any]]
    """Per-tool statistics: {tool_name: {call_count, success_rate, average_time}}."""

    @classmethod
    def from_agent_result(cls, result: AgentResult) -> AgentLoopMetrics:
        """Extract metrics from a Strands AgentResult.

        Args:
            result: The AgentResult returned at the end of an agent invocation.

        Returns:
            Normalized AgentLoopMetrics instance.
        """
        summary = result.metrics.get_summary()
        usage = summary.get("accumulated_usage", {})
        metrics_data = summary.get("accumulated_metrics", {})

        return cls(
            total_cycles=summary.get("total_cycles", 0),
            total_duration_ms=metrics_data.get("latencyMs", 0),
            input_tokens=usage.get("inputTokens", 0),
            output_tokens=usage.get("outputTokens", 0),
            total_tokens=usage.get("totalTokens", 0),
            stop_reason=result.stop_reason,
            tool_stats=summary.get("tool_usage", {}),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AgentLoopMetrics:
        """Reconstruct from a dictionary (e.g., loaded from JSON)."""
        return cls(
            total_cycles=data.get("total_cycles", 0),
            total_duration_ms=data.get("total_duration_ms", 0),
            input_tokens=data.get("input_tokens", 0),
            output_tokens=data.get("output_tokens", 0),
            total_tokens=data.get("total_tokens", 0),
            stop_reason=data.get("stop_reason", "unknown"),
            tool_stats=data.get("tool_stats", {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def format_summary(self) -> str:
        """Format metrics as a human-readable summary string.

        Returns:
            String like "Tokens: 150 in / 89 out | Cycles: 2 | 1.2s"
        """
        duration_s = self.total_duration_ms / 1000
        return (
            f"Tokens: {self.input_tokens} in / {self.output_tokens} out | "
            f"Cycles: {self.total_cycles} | {duration_s:.1f}s"
        )

    def format_tool_summary(self) -> str:
        """Format tool usage as a summary string.

        Returns:
            String like "Tools: search (3 calls), fetch (2 calls)"
        """
        if not self.tool_stats:
            return "Tools: none"

        parts = []
        for name, stats in self.tool_stats.items():
            count = stats.get("call_count", 0)
            parts.append(f"{name} ({count})")
        return f"Tools: {', '.join(parts)}"


def extract_metrics_from_event(event: dict[str, Any]) -> AgentLoopMetrics | None:
    """Extract metrics from a streaming event if it contains an AgentResult.

    The final event from stream_async contains {"result": AgentResult}.

    Args:
        event: A streaming event dictionary.

    Returns:
        AgentLoopMetrics if the event contains a result, None otherwise.
    """
    result = event.get("result")
    if result is None:
        return None

    # The result should be an AgentResult instance
    if hasattr(result, "metrics") and hasattr(result, "stop_reason"):
        return AgentLoopMetrics.from_agent_result(result)

    return None
