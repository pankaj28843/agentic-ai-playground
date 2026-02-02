from agent_toolkit.tools.registry import ToolDefinition, ToolRegistry


def _make_tool(name: str, description: str, category: str = "general"):
    def handler():
        return name

    return ToolDefinition(
        name=name,
        description=description,
        category=category,
        tags=("alpha",),
        capabilities=("read",),
    ), handler


def test_register_and_get_tool() -> None:
    registry = ToolRegistry()
    definition, handler = _make_tool("alpha", "Alpha tool")
    registry.register(definition, handler)

    entry = registry.get("alpha")
    assert entry is not None
    assert entry.definition.name == "alpha"
    assert entry.handler is handler


def test_list_detail_levels() -> None:
    registry = ToolRegistry()
    definition, handler = _make_tool("alpha", "Alpha tool")
    registry.register(definition, handler)

    name_only = registry.list(detail_level="name")
    assert name_only == [{"name": "alpha"}]

    summary = registry.list(detail_level="summary")[0]
    assert summary["name"] == "alpha"
    assert summary["description"] == "Alpha tool"
    assert "input_schema" not in summary

    full = registry.list(detail_level="full")[0]
    assert full["name"] == "alpha"
    assert full["description"] == "Alpha tool"
    assert "input_schema" in full


def test_list_by_category_groups() -> None:
    registry = ToolRegistry()
    tool_a, handler_a = _make_tool("alpha", "Alpha tool", category="group-a")
    tool_b, handler_b = _make_tool("beta", "Beta tool", category="group-b")
    registry.register(tool_a, handler_a)
    registry.register(tool_b, handler_b)

    grouped = registry.list_by_category()
    assert set(grouped.keys()) == {"group-a", "group-b"}


def test_search_matches_multiple_fields() -> None:
    registry = ToolRegistry()
    definition, handler = _make_tool("alpha", "Alpha tool")
    registry.register(definition, handler)

    assert registry.search("alpha")
    assert registry.search("ALPHA")
    assert registry.search("tool")
    assert registry.search("read")
    assert registry.search("alpha", detail_level="name") == [{"name": "alpha"}]


def test_to_strands_tools_filtering() -> None:
    registry = ToolRegistry()
    tool_a, handler_a = _make_tool("alpha", "Alpha tool")
    tool_b, handler_b = _make_tool("beta", "Beta tool")
    registry.register(tool_a, handler_a)
    registry.register(tool_b, handler_b)

    all_tools = registry.to_strands_tools()
    assert handler_a in all_tools
    assert handler_b in all_tools

    filtered = registry.to_strands_tools(["beta", "missing"])
    assert filtered == [handler_b]
