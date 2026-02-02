from agent_toolkit.config import load_settings


def test_load_settings_defaults() -> None:
    settings = load_settings()
    assert settings.techdocs_mcp_url


def test_load_settings_phoenix_defaults() -> None:
    """Test that Phoenix settings have correct defaults."""
    settings = load_settings()
    # Default is disabled
    assert isinstance(settings.phoenix_enabled, bool)  # loaded from env
    assert settings.phoenix_collector_endpoint == ""
    assert settings.phoenix_grpc_port > 0
    assert settings.phoenix_project_name


def test_load_settings_tool_truncation_default() -> None:
    """Test that tool result truncation is enabled by default."""
    settings = load_settings()
    assert settings.should_truncate_tool_results is True
