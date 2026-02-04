"""Tests for MCP provider registry."""

from pathlib import Path

from agent_toolkit.mcp.registry import MCPProviderRegistry


def test_registry_loads_enabled_provider(tmp_path: Path) -> None:
    config_path = tmp_path / "mcp_providers.toml"
    config_path.write_text(
        """
[techdocs]
name = "TechDocs"
url_default = "http://localhost:9000"
enabled = true

[disabled]
url_default = "http://localhost:9001"
enabled = false
""".lstrip()
    )

    registry = MCPProviderRegistry(config_path=config_path)
    providers = registry.providers

    assert "techdocs" in providers
    assert "disabled" not in providers
    assert providers["techdocs"].url.rstrip("/") == "http://localhost:9000"


def test_registry_reads_headers_from_env(tmp_path: Path, monkeypatch) -> None:
    config_path = tmp_path / "mcp_providers.toml"
    config_path.write_text(
        """
[custom]
url_env = "CUSTOM_MCP_URL"
headers_env = "CUSTOM_MCP_HEADERS"
""".lstrip()
    )
    monkeypatch.setenv("CUSTOM_MCP_URL", "http://localhost:9999")
    monkeypatch.setenv("CUSTOM_MCP_HEADERS", '{"Authorization": "Bearer token"}')

    registry = MCPProviderRegistry(config_path=config_path)
    providers = registry.providers

    assert providers["custom"].url.rstrip("/") == "http://localhost:9999"
    assert providers["custom"].headers == {"Authorization": "Bearer token"}
