from agent_toolkit.config import load_profiles


def test_load_profiles_contains_defaults() -> None:
    """Test that profiles load from config and have expected structure."""
    profiles = load_profiles()
    # Should have at least one profile
    assert len(profiles) > 0
    # Check the general agent exists (from config/agents.toml)
    assert "general" in profiles
    profile = profiles["general"]
    assert isinstance(profile.tool_groups, list)
    assert isinstance(profile.metadata, dict)
