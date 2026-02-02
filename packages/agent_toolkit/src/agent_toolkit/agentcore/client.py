from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AgentCoreConfig:
    """Configuration for AgentCore runtime calls."""

    region: str
    runtime_id: str


class AgentCoreClient:
    """Placeholder client for AgentCore runtime."""

    def __init__(self, config: AgentCoreConfig) -> None:
        """Store configuration for future calls."""
        self._config = config

    def invoke(self, prompt: str) -> str:
        """Invoke the AgentCore runtime (not yet implemented)."""
        message = "AgentCore transport is not yet implemented."
        raise NotImplementedError(message)
