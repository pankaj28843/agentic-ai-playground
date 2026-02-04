import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest
from agent_toolkit.memory import MemoryConfig, build_memory_session_manager


def _install_agentcore_stubs(monkeypatch: pytest.MonkeyPatch) -> tuple[MagicMock, MagicMock]:
    mock_config = MagicMock()
    mock_manager = MagicMock()
    module_tree = {
        "bedrock_agentcore": ModuleType("bedrock_agentcore"),
        "bedrock_agentcore.memory": ModuleType("bedrock_agentcore.memory"),
        "bedrock_agentcore.memory.integrations": ModuleType(
            "bedrock_agentcore.memory.integrations"
        ),
        "bedrock_agentcore.memory.integrations.strands": ModuleType(
            "bedrock_agentcore.memory.integrations.strands"
        ),
        "bedrock_agentcore.memory.integrations.strands.config": ModuleType(
            "bedrock_agentcore.memory.integrations.strands.config"
        ),
        "bedrock_agentcore.memory.integrations.strands.session_manager": ModuleType(
            "bedrock_agentcore.memory.integrations.strands.session_manager"
        ),
    }
    module_tree["bedrock_agentcore"].__path__ = []
    module_tree["bedrock_agentcore.memory"].__path__ = []
    module_tree["bedrock_agentcore.memory.integrations"].__path__ = []
    module_tree["bedrock_agentcore.memory.integrations.strands"].__path__ = []
    module_tree[
        "bedrock_agentcore.memory.integrations.strands.config"
    ].AgentCoreMemoryConfig = mock_config
    module_tree[
        "bedrock_agentcore.memory.integrations.strands.session_manager"
    ].AgentCoreMemorySessionManager = mock_manager
    monkeypatch.setitem(sys.modules, "bedrock_agentcore", module_tree["bedrock_agentcore"])
    monkeypatch.setitem(
        sys.modules, "bedrock_agentcore.memory", module_tree["bedrock_agentcore.memory"]
    )
    monkeypatch.setitem(
        sys.modules,
        "bedrock_agentcore.memory.integrations",
        module_tree["bedrock_agentcore.memory.integrations"],
    )
    monkeypatch.setitem(
        sys.modules,
        "bedrock_agentcore.memory.integrations.strands",
        module_tree["bedrock_agentcore.memory.integrations.strands"],
    )
    monkeypatch.setitem(
        sys.modules,
        "bedrock_agentcore.memory.integrations.strands.config",
        module_tree["bedrock_agentcore.memory.integrations.strands.config"],
    )
    monkeypatch.setitem(
        sys.modules,
        "bedrock_agentcore.memory.integrations.strands.session_manager",
        module_tree["bedrock_agentcore.memory.integrations.strands.session_manager"],
    )
    return mock_config, mock_manager


def test_memory_adapter_none() -> None:
    config = MemoryConfig(session_id="session")
    assert build_memory_session_manager("none", config) is None


def test_memory_adapter_agentcore_requires_memory_id(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_agentcore_stubs(monkeypatch)
    config = MemoryConfig(session_id="session")
    monkeypatch.delenv("AGENTCORE_MEMORY_ID", raising=False)
    with pytest.raises(RuntimeError, match="AGENTCORE_MEMORY_ID"):
        build_memory_session_manager("agentcore", config)


def test_memory_adapter_agentcore_uses_env(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_config, mock_manager = _install_agentcore_stubs(monkeypatch)
    monkeypatch.setenv("AGENTCORE_MEMORY_ID", "memory-123")
    monkeypatch.setenv("AWS_REGION", "us-west-2")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")

    config = MemoryConfig(session_id="session")
    result = build_memory_session_manager("agentcore", config)

    assert result is mock_manager.return_value
    mock_config.assert_called_once_with(
        memory_id="memory-123",
        session_id="session",
        actor_id="session",
    )
    mock_manager.assert_called_once_with(
        agentcore_memory_config=mock_config.return_value,
        region_name="us-west-2",
    )
