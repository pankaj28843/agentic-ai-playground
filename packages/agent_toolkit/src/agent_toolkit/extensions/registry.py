"""Extension event registry with safe execution."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from agent_toolkit.extensions.models import ExtensionError

EventHandler = Callable[[dict[str, Any]], Any]


class ExtensionRegistry:
    """Register and emit extension events with error isolation."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[tuple[str, EventHandler]]] = defaultdict(list)
        self.errors: list[ExtensionError] = []

    def on(self, event_name: str, extension_name: str, handler: EventHandler) -> None:
        """Register an event handler for an extension."""
        self._handlers[event_name].append((extension_name, handler))

    def emit(self, event_name: str, payload: dict[str, Any]) -> list[Any]:
        """Emit an event and collect handler results."""
        results: list[Any] = []
        for extension_name, handler in self._handlers.get(event_name, []):
            try:
                results.append(handler(payload))
            except Exception as exc:  # noqa: BLE001 - defensive isolation
                self.errors.append(
                    ExtensionError(
                        extension_name=extension_name,
                        event_name=event_name,
                        message=str(exc),
                    )
                )
        return results
