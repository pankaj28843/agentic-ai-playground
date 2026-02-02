import textwrap

from agent_toolkit import AgentRuntime


def test_agent_runtime_loads_profiles_from_external_dir(tmp_path, monkeypatch) -> None:
    """Test that runtime loads profiles from external config dir using new schema."""
    # New schema: agents.toml defines atomic agents
    agents_toml = textwrap.dedent(
        """
        [agents.external]
        system_prompt = "External prompt"
        model = ""
        tools = []
        tool_groups = []
        [agents.external.metadata]
        description = "External agent"
        """
    )
    # New schema: public_profiles.toml defines UI-visible profiles
    public_profiles_toml = textwrap.dedent(
        """
        [public_profiles.external]
        name = "External"
        description = "External profile for testing"
        entrypoint_type = "single"
        entrypoint_reference = "external"
        default = false
        """
    )
    # Empty files to prevent loader errors
    (tmp_path / "agents.toml").write_text(agents_toml, encoding="utf-8")
    (tmp_path / "public_profiles.toml").write_text(public_profiles_toml, encoding="utf-8")
    (tmp_path / "graphs.toml").write_text("", encoding="utf-8")
    (tmp_path / "swarms.toml").write_text("", encoding="utf-8")
    (tmp_path / "tool_groups.toml").write_text("", encoding="utf-8")
    monkeypatch.setenv("PLAYGROUND_CONFIG_DIR", str(tmp_path))

    runtime = AgentRuntime()
    profile_names = {profile.name for profile in runtime.list_profiles()}
    assert "external" in profile_names
