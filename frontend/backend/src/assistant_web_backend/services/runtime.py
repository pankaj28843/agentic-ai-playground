"""Agent runtime provider.

Creates and caches the AgentRuntime instance with a DI-friendly interface.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

logger = logging.getLogger(__name__)


def _load_runtime_class() -> Any:
    """Lazy load AgentRuntime to avoid import cycles."""
    from agent_toolkit.runtime import AgentRuntime as _AgentRuntime  # noqa: PLC0415

    return _AgentRuntime


@lru_cache
def get_runtime() -> Any:
    """Return a cached AgentRuntime instance."""
    runtime_class = _load_runtime_class()
    if runtime_class is None:
        message = "Agent runtime is unavailable"
        raise RuntimeError(message)
    runtime = runtime_class()
    logger.info("AgentRuntime initialized (Phoenix telemetry should be active)")
    return runtime


def is_available() -> bool:
    """Check if the runtime is available."""
    return _load_runtime_class() is not None
