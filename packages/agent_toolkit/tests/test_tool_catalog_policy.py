from agent_toolkit.config.service import ConfigService
from agent_toolkit.tools import DEFAULT_TOOL_REGISTRY, ToolCatalog


def test_tool_catalog_denies_capability(monkeypatch) -> None:
    monkeypatch.setenv("CAPABILITY_DENYLIST", "delegate")
    service = ConfigService()
    catalog = ToolCatalog(DEFAULT_TOOL_REGISTRY, service)
    selection = catalog.expand_tools("general")
    assert "subagent" not in selection.tools
    assert "subagents" not in selection.tool_groups


def test_tool_catalog_allowlist_filters_groups(monkeypatch) -> None:
    monkeypatch.setenv("CAPABILITY_ALLOWLIST", "read")
    service = ConfigService()
    catalog = ToolCatalog(DEFAULT_TOOL_REGISTRY, service)
    selection = catalog.expand_tools("general")
    assert "subagent" not in selection.tools
    assert "subagents" not in selection.tool_groups
