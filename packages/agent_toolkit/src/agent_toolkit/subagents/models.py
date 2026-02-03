"""Subagent models."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SubagentDefinition:
    """Definition for a subagent loaded from markdown."""

    name: str
    description: str
    system_prompt: str
    model: str
    tools: list[str] = field(default_factory=list)
    tool_groups: list[str] = field(default_factory=list)
    source: str = ""


@dataclass(frozen=True)
class SubagentTask:
    """Execution task for a subagent."""

    agent: str
    prompt: str
    model_override: str | None = None


@dataclass(frozen=True)
class SubagentResult:
    """Result payload returned from a subagent run."""

    agent: str
    prompt: str
    output: str
    error: str | None = None
