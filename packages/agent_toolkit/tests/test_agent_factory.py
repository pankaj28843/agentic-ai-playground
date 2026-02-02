from unittest.mock import MagicMock, patch

from agent_toolkit.agents.factory import AgentFactory
from agent_toolkit.config import AgentProfile, load_settings
from agent_toolkit.tools.registry import ToolDefinition, ToolRegistry


def _register_tool(registry: ToolRegistry, name: str) -> None:
    def handler():
        return name

    registry.register(ToolDefinition(name=name, description=f"{name} tool"), handler)


@patch("strands.Agent")
def test_agent_factory_creates_agent_from_profile(mock_agent_cls: MagicMock) -> None:
    mock_agent = MagicMock()
    mock_agent.name = "dummy-agent"
    mock_agent_cls.return_value = mock_agent

    settings = load_settings()
    registry = ToolRegistry()
    _register_tool(registry, "dummy")

    profile = AgentProfile(
        name="dummy-agent",
        description="Dummy",
        model="",
        system_prompt="Hello",
        tools=["dummy"],
        tool_groups=[],
        extends="",
        metadata={},
        constraints={},
    )
    agent = AgentFactory(settings=settings, registry=registry).create_from_profile(profile)

    assert agent.name == "dummy-agent"
    mock_agent_cls.assert_called_once()


def test_agent_factory_creates_specialist_tool() -> None:
    settings = load_settings()
    registry = ToolRegistry()
    _register_tool(registry, "dummy")

    factory = AgentFactory(settings=settings, registry=registry)
    tool_fn = factory.create_specialist_tool_agent(
        name="specialist",
        description="Specialist tool",
        system_prompt="Be helpful.",
        tool_names=["dummy"],
    )

    assert callable(tool_fn)
    assert registry.get("specialist") is not None
