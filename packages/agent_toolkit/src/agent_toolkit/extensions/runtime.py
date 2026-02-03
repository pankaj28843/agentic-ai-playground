"""Extension runtime for loading and executing extensions."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING

from agent_toolkit.extensions.api import ExtensionAPI
from agent_toolkit.extensions.registry import ExtensionRegistry

if TYPE_CHECKING:
    from agent_toolkit.extensions.models import ExtensionCommand
    from agent_toolkit.tools.registry import ToolRegistry

ExtensionFactory = Callable[[ExtensionAPI], None]


class ExtensionRuntime:
    """Loads extensions and manages event emission."""

    def __init__(self, tool_registry: ToolRegistry) -> None:
        self._registry = ExtensionRegistry()
        self._tool_registry = tool_registry
        self._commands: dict[str, ExtensionCommand] = {}

    @property
    def errors(self) -> list:
        """Return collected extension errors."""
        return self._registry.errors

    @property
    def commands(self) -> dict[str, ExtensionCommand]:
        """Return registered extension commands."""
        return dict(self._commands)

    def load_extensions(self, factories: Iterable[tuple[str, ExtensionFactory]]) -> None:
        """Load extensions from the provided factories."""
        for name, factory in factories:
            api = ExtensionAPI(
                name=name, registry=self._registry, tool_registry=self._tool_registry
            )
            factory(api)
            self._commands.update(api.commands)

    def emit(self, event_name: str, payload: dict) -> list:
        """Emit an extension event and return handler outputs."""
        return self._registry.emit(event_name, payload)
