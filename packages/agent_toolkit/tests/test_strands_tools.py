"""Tests for strands tools adapter."""

import pytest
from agent_toolkit.tools.strands_tools import (
    STRANDS_TOOL_GROUPS,
    STRANDS_TOOLS_CATALOG,
    import_strands_tool,
    list_available_tools,
    list_tool_groups,
)


class TestStrandsToolsCatalog:
    """Tests for strands tools catalog."""

    def test_catalog_has_common_tools(self) -> None:
        """Verify common tools are in the catalog."""
        assert "current_time" in STRANDS_TOOLS_CATALOG
        assert "file_read" in STRANDS_TOOLS_CATALOG
        assert "shell" in STRANDS_TOOLS_CATALOG
        assert "http_request" in STRANDS_TOOLS_CATALOG

    def test_tool_groups_defined(self) -> None:
        """Verify tool groups are defined."""
        assert "basic" in STRANDS_TOOL_GROUPS
        assert "files" in STRANDS_TOOL_GROUPS
        assert "shell" in STRANDS_TOOL_GROUPS
        assert "web" in STRANDS_TOOL_GROUPS

    def test_list_available_tools(self) -> None:
        """Test list_available_tools returns all tools."""
        tools = list_available_tools()
        assert len(tools) > 20
        assert "current_time" in tools

    def test_list_tool_groups(self) -> None:
        """Test list_tool_groups returns all groups."""
        groups = list_tool_groups()
        assert "basic" in groups
        assert "current_time" in groups["basic"]


class TestImportStrandsTool:
    """Tests for importing strands tools."""

    def test_import_unknown_tool_returns_none(self) -> None:
        """Unknown tools return None."""
        result = import_strands_tool("nonexistent_tool_xyz")
        assert result is None

    def test_import_current_time(self) -> None:
        """Test importing a real tool if available."""
        pytest.importorskip("strands_tools")
        tool = import_strands_tool("current_time")
        assert tool is not None
        assert callable(tool)
