from agent_toolkit.agents.builders import build_session_manager
from agent_toolkit.config import Settings
from strands.session.file_session_manager import FileSessionManager


def test_build_session_manager_file() -> None:
    settings = Settings(
        techdocs_mcp_url="http://example",
        bedrock_model_id="model",
        playground_config_dir="",
        conversation_manager="sliding",
        sliding_window_size=5,
        summary_ratio=0.3,
        preserve_recent_messages=5,
        session_manager="file",
        session_storage_dir="",
        approval_tools=[],
        run_mode="graph",
        single_execution_timeout=120.0,
        graph_execution_timeout=300.0,
        graph_node_timeout=90.0,
        swarm_execution_timeout=300.0,
        swarm_node_timeout=90.0,
        swarm_max_handoffs=12,
        swarm_max_iterations=12,
        swarm_preset="default",
        phoenix_enabled=False,
        phoenix_collector_endpoint="https://phoenix.example.com",
        phoenix_public_url="https://phoenix.example.com",
        phoenix_grpc_port=4317,
        phoenix_project_name="test",
        online_eval_enabled=False,
        online_eval_model="bedrock/eu.amazon.nova-micro-v1:0",
        online_eval_temperature=0.0,
        online_eval_max_tokens=256,
        online_eval_sample_rate=0.1,
        should_truncate_tool_results=True,
    )
    session_manager = build_session_manager(settings, "demo")
    assert isinstance(session_manager, FileSessionManager)
