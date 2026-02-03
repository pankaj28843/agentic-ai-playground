from agent_toolkit.runtime import AgentRuntime


def test_profile_overrides_apply_model_and_tool_groups() -> None:
    runtime = AgentRuntime()
    profile = runtime.list_profiles()[0]

    updated = runtime.apply_profile_overrides(
        profile,
        model_override="bedrock.nova-pro",
        tool_groups_override=["strands_basic"],
    )

    assert updated.model == "bedrock.nova-pro"
    assert updated.tool_groups == ["strands_basic"]
    assert "strands:calculator" in updated.tools


def test_profile_overrides_noop_returns_profile() -> None:
    runtime = AgentRuntime()
    profile = runtime.list_profiles()[0]

    updated = runtime.apply_profile_overrides(profile, None, None)

    assert updated is profile
