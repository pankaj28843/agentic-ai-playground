from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

JSONSchema = dict[str, Any]
ToolDetailLevel = Literal["name", "summary", "full"]


def _normalize_items(items: Iterable[str] | str | None) -> tuple[str, ...]:
    if items is None:
        return ()
    if isinstance(items, str):
        stripped = items.strip()
        return (stripped,) if stripped else ()
    normalized: list[str] = []
    for item in items:
        value = str(item).strip()
        if value and value not in normalized:
            normalized.append(value)
    return tuple(normalized)


def _validate_json_schema(schema: Mapping[str, Any], label: str) -> None:
    if not isinstance(schema, Mapping):
        message = f"{label} must be a mapping"
        raise TypeError(message)
    schema_type = schema.get("type")
    properties = schema.get("properties")
    if properties is not None:
        if schema_type not in (None, "object"):
            message = f"{label}.properties requires type 'object'"
            raise ValueError(message)
        if not isinstance(properties, Mapping):
            message = f"{label}.properties must be a mapping when provided"
            raise ValueError(message)
    required = schema.get("required")
    if required is not None and not isinstance(required, list):
        message = f"{label}.required must be a list when provided"
        raise ValueError(message)
    if isinstance(required, list):
        if properties is None:
            message = f"{label}.required requires properties to be defined"
            raise ValueError(message)
        for key in required:
            if key not in properties:
                message = f"{label}.required contains unknown property '{key}'"
                raise ValueError(message)


@dataclass(frozen=True)
class ToolDefinition:
    """Metadata describing a tool in the registry."""

    name: str
    description: str
    category: str = "general"
    tags: tuple[str, ...] = ()
    input_schema: JSONSchema | None = None
    output_schema: JSONSchema | None = None
    capabilities: tuple[str, ...] = ()
    requires_approval: bool = False
    source: str = "local"

    def __post_init__(self) -> None:
        if not self.name.strip():
            msg = "ToolDefinition.name must be non-empty"
            raise ValueError(msg)
        if not self.description.strip():
            msg = "ToolDefinition.description must be non-empty"
            raise ValueError(msg)
        if not self.category.strip():
            object.__setattr__(self, "category", "general")
        object.__setattr__(self, "tags", _normalize_items(self.tags))
        object.__setattr__(self, "capabilities", _normalize_items(self.capabilities))
        if self.input_schema is not None:
            _validate_json_schema(self.input_schema, "input_schema")
        if self.output_schema is not None:
            _validate_json_schema(self.output_schema, "output_schema")

    def validate(self) -> None:
        """Re-validate the tool definition."""
        if self.input_schema is not None:
            _validate_json_schema(self.input_schema, "input_schema")
        if self.output_schema is not None:
            _validate_json_schema(self.output_schema, "output_schema")

    def to_dict(self, detail_level: ToolDetailLevel = "full") -> dict[str, Any]:
        """Convert tool definition to dict with specified detail level."""
        payload: dict[str, Any] = {"name": self.name}
        if detail_level in ("summary", "full"):
            payload.update(
                {
                    "description": self.description,
                    "category": self.category,
                    "tags": list(self.tags),
                    "capabilities": list(self.capabilities),
                    "requires_approval": self.requires_approval,
                    "source": self.source,
                }
            )
        if detail_level == "full":
            payload["input_schema"] = self.input_schema
            payload["output_schema"] = self.output_schema
        return payload


@dataclass(frozen=True)
class RegisteredTool:
    """Tool definition paired with its callable implementation."""

    definition: ToolDefinition
    handler: Callable[..., Any]


class ToolRegistry:
    """Registry for tools and their metadata definitions."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, definition: ToolDefinition, handler: Callable[..., Any]) -> None:
        """Register a tool definition and handler."""
        if definition.name in self._tools:
            message = f"Tool already registered: {definition.name}"
            raise ValueError(message)
        self._tools[definition.name] = RegisteredTool(definition=definition, handler=handler)

    def get(self, name: str) -> RegisteredTool | None:
        """Get a registered tool by name."""
        return self._tools.get(name)

    def list(self, detail_level: ToolDetailLevel = "full") -> list[dict[str, Any]]:
        """List registered tools at the requested detail level."""
        return [entry.definition.to_dict(detail_level) for entry in self._tools.values()]

    def list_by_category(
        self, detail_level: ToolDetailLevel = "summary"
    ) -> dict[str, list[dict[str, Any]]]:
        """List tools grouped by category."""
        grouped: dict[str, list[dict[str, Any]]] = {}
        for entry in self._tools.values():
            category = entry.definition.category
            grouped.setdefault(category, []).append(entry.definition.to_dict(detail_level))
        return grouped

    def search(self, query: str, detail_level: ToolDetailLevel = "summary") -> list[dict[str, Any]]:
        """Search tools by name, description, tags, or capabilities."""
        needle = query.strip().lower()
        if not needle:
            return []
        results: list[dict[str, Any]] = []
        for entry in self._tools.values():
            definition = entry.definition
            haystack = " ".join(
                [
                    definition.name,
                    definition.description,
                    definition.category,
                    " ".join(definition.tags),
                    " ".join(definition.capabilities),
                ]
            ).lower()
            if needle in haystack:
                results.append(definition.to_dict(detail_level))
        return results

    def to_strands_tools(self, names: Iterable[str] | None = None) -> list[Callable[..., Any]]:
        """Return Strands-compatible tool callables, optionally filtered by name.

        Supports "strands:" prefix for tools from strands-agents-tools package.
        Example: "strands:file_read" imports file_read from strands_tools.
        """
        if names is None:
            return [entry.handler for entry in self._tools.values()]

        resolved: list[Callable[..., Any]] = []
        for name in names:
            # Check for strands: prefix (external strands-agents-tools)
            if name.startswith("strands:"):
                tool_name = name[8:]  # Remove "strands:" prefix
                from agent_toolkit.tools.strands_tools import (  # noqa: PLC0415
                    import_strands_tool,
                )

                tool = import_strands_tool(tool_name)
                if tool is not None:
                    resolved.append(tool)
            else:
                # Local registry tool
                entry = self._tools.get(name)
                if entry is not None:
                    resolved.append(entry.handler)
        return resolved


DEFAULT_TOOL_REGISTRY = ToolRegistry()


def register_tool(
    definition: ToolDefinition,
    handler: Callable[..., Any],
    registry: ToolRegistry | None = None,
) -> Callable[..., Any]:
    """Register a tool definition and return the handler for decorator chaining."""
    target = registry or DEFAULT_TOOL_REGISTRY
    target.register(definition, handler)
    return handler


def registered_tool(
    *,
    name: str | None = None,
    description: str | None = None,
    category: str = "general",
    tags: Iterable[str] | str | None = None,
    input_schema: JSONSchema | None = None,
    output_schema: JSONSchema | None = None,
    capabilities: Iterable[str] | str | None = None,
    requires_approval: bool = False,
    source: str = "local",
    registry: ToolRegistry | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that wraps a Strands tool and registers metadata in the registry."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        from strands import tool as strands_tool  # noqa: PLC0415

        tool_func = strands_tool(func)
        tool_name = name or getattr(func, "__name__", "").strip()
        tool_description = description or (getattr(func, "__doc__", "") or "").strip()
        if not tool_description:
            msg = "Tool description must be provided or via docstring"
            raise ValueError(msg)
        definition = ToolDefinition(
            name=tool_name,
            description=tool_description,
            category=category,
            tags=tags,
            input_schema=input_schema,
            output_schema=output_schema,
            capabilities=capabilities,
            requires_approval=requires_approval,
            source=source,
        )
        return register_tool(definition, tool_func, registry=registry)

    return decorator
