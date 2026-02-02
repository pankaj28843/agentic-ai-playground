import pytest
from agent_toolkit.tools.registry import ToolDefinition


def test_tool_definition_minimal_valid() -> None:
    tool = ToolDefinition(name="example", description="Example tool")
    tool.validate()


def test_tool_definition_requires_name() -> None:
    with pytest.raises(ValueError, match="name must be non-empty"):
        ToolDefinition(name="", description="Example")


def test_tool_definition_rejects_bad_schema_type() -> None:
    with pytest.raises(TypeError, match="input_schema must be a mapping"):
        ToolDefinition(name="example", description="Example", input_schema="nope")


def test_tool_definition_rejects_unknown_required() -> None:
    with pytest.raises(ValueError, match="required contains unknown property"):
        ToolDefinition(
            name="example",
            description="Example",
            input_schema={
                "type": "object",
                "properties": {"q": {"type": "string"}},
                "required": ["missing"],
            },
        )
