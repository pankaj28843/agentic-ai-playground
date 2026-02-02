from agent_toolkit.memory import MemoryConfig, build_memory_session_manager


def test_memory_adapter_none() -> None:
    config = MemoryConfig(session_id="session")
    assert build_memory_session_manager("none", config) is None
