"""Extension API for registering hooks, tools, and commands."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

from agent_toolkit.extensions.models import ExtensionCommand

if TYPE_CHECKING:
    from agent_toolkit.extensions.registry import ExtensionRegistry
    from agent_toolkit.tools.registry import ToolDefinition, ToolRegistry


class ExtensionAPI:
    """API passed to extensions for registration."""

    def __init__(self, name: str, registry: ExtensionRegistry, tool_registry: ToolRegistry) -> None:
        self._name = name
        self._registry = registry
        self._tool_registry = tool_registry
        self.commands: dict[str, ExtensionCommand] = {}

    def on(self, event_name: str, handler: Callable[[dict[str, Any]], Any]) -> None:
        """Register an event handler."""
        self._registry.on(event_name, self._name, handler)

    def register_tool(self, definition: ToolDefinition, handler: Callable[..., Any]) -> None:
        """Register a tool in the shared ToolRegistry."""
        self._tool_registry.register(definition, handler)

    def register_command(self, name: str, description: str, handler: Callable[[str], Any]) -> None:
        """Register a command callable by name."""
        self.commands[name] = ExtensionCommand(name=name, description=description, handler=handler)
