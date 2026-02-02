from agent_toolkit.tools.registry import (
    ToolDefinition,
    ToolRegistry,
    register_tool,
    registered_tool,
)


def test_registered_tool_decorator_registers() -> None:
    registry = ToolRegistry()

    @registered_tool(description="Example tool", registry=registry)
    def example_tool() -> str:
        """Example tool docstring."""
        return "ok"

    entry = registry.get("example_tool")
    assert entry is not None
    assert entry.definition.description == "Example tool"
    assert entry.handler is example_tool


def test_register_tool_helper_registers() -> None:
    registry = ToolRegistry()

    def raw_tool() -> str:
        return "ok"

    definition = ToolDefinition(name="raw_tool", description="Raw tool")
    register_tool(definition, raw_tool, registry=registry)

    entry = registry.get("raw_tool")
    assert entry is not None
    assert entry.handler is raw_tool
