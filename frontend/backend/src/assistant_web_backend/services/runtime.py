"""Agent runtime service.

Manages the singleton AgentRuntime instance and provides runtime operations.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from agent_toolkit.runtime import AgentRuntime as _AgentRuntime

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
AgentRuntime: Any = _AgentRuntime


def _load_runtime_class() -> Any:
    """Lazy load AgentRuntime to avoid import cycles."""
    global AgentRuntime  # noqa: PLW0603
    if AgentRuntime is None:
        from agent_toolkit.runtime import AgentRuntime as _AgentRuntime  # noqa: PLC0415

        AgentRuntime = _AgentRuntime
    return AgentRuntime


# Singleton AgentRuntime - initialized once at module load.
# This ensures Phoenix telemetry is set up BEFORE any boto3/Bedrock clients are created.
_runtime: Any = None
_runtime_lock = threading.Lock()


class RuntimeService:
    """Service for managing the agent runtime singleton."""

    @staticmethod
    def get_runtime() -> Any:
        """Get or create the singleton AgentRuntime instance (thread-safe)."""
        global _runtime  # noqa: PLW0603
        if _runtime is None:
            with _runtime_lock:
                if _runtime is None:  # Double-checked locking
                    runtime_class = _load_runtime_class()
                    if runtime_class is None:
                        message = "Agent runtime is unavailable"
                        raise RuntimeError(message)
                    _runtime = runtime_class()
                    logger.info("AgentRuntime initialized (Phoenix telemetry should be active)")
        return _runtime

    @staticmethod
    def is_available() -> bool:
        """Check if the runtime is available."""
        return _load_runtime_class() is not None
