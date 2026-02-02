from unittest.mock import MagicMock, patch

from agent_toolkit import AgentRuntime


@patch("strands.Agent")
def test_runtime_uses_registry_for_profile_tools(mock_agent_cls: MagicMock) -> None:
    """Test that runtime creates agents from configured profiles."""
    mock_agent = MagicMock()
    mock_agent.name = "general"
    mock_agent_cls.return_value = mock_agent

    runtime = AgentRuntime()
    # Use "general" which is defined in config/agents.toml
    _ = runtime.create_agent("general")

    # Verify the factory was called with tools
    mock_agent_cls.assert_called_once()
    call_kwargs = mock_agent_cls.call_args[1]
    assert "tools" in call_kwargs
    # Tools now come from MCPClient - should have at least one tool provider
    assert len(call_kwargs["tools"]) > 0
