"""Pydantic models for application settings."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from pydantic import BaseModel, Field


class Settings(BaseModel, frozen=True):
    """Runtime configuration loaded from environment variables."""

    techdocs_mcp_url: str = ""
    bedrock_model_id: str = "bedrock.nova-lite"
    playground_config_dir: str
    conversation_manager: str = "sliding"
    sliding_window_size: int = 12
    summary_ratio: float = 0.3
    preserve_recent_messages: int = 10
    session_manager: str = "file"
    session_storage_dir: str = ".data/sessions"
    approval_tools: list[str] = Field(default_factory=list)
    run_mode: str = "quick"
    single_execution_timeout: float = 120.0
    graph_execution_timeout: float = 300.0
    graph_node_timeout: float = 90.0
    swarm_execution_timeout: float = 300.0
    swarm_node_timeout: float = 90.0
    swarm_max_handoffs: int = 12
    swarm_max_iterations: int = 12
    swarm_preset: str = "default"
    # Phoenix telemetry settings
    phoenix_enabled: bool = False
    phoenix_collector_endpoint: str = ""
    phoenix_grpc_port: int = 4317
    phoenix_project_name: str = "agentic-ai-playground"
    phoenix_public_url: str | None = None
    # Online evaluation settings
    online_eval_enabled: bool = False
    online_eval_model: str = "bedrock.nova-micro"
    online_eval_temperature: float = 0.0
    online_eval_max_tokens: int = 256
    online_eval_sample_rate: float = 0.1
    # Tool result handling
    should_truncate_tool_results: bool = True


def _parse_list(value: str) -> list[str]:
    """Parse comma-separated string into list."""
    return [item.strip() for item in value.split(",") if item.strip()]


def load_settings() -> Settings:
    """Load settings from environment variables with defaults."""
    load_dotenv()

    techdocs_mcp_url = os.getenv("TECHDOCS_MCP_URL")
    if not techdocs_mcp_url:
        msg = (
            "TECHDOCS_MCP_URL environment variable is required. "
            "Point it at your TechDocs MCP endpoint."
        )
        raise ValueError(msg)

    # Enforce mandatory PLAYGROUND_CONFIG_DIR
    config_dir = os.getenv("PLAYGROUND_CONFIG_DIR")
    if not config_dir:
        msg = (
            "PLAYGROUND_CONFIG_DIR environment variable is required. "
            "Set it to './config' for repo root configs or copy from .env.example"
        )
        raise ValueError(msg)

    phoenix_enabled = os.getenv("PHOENIX_ENABLED", "false").lower() == "true"
    phoenix_collector_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")
    if phoenix_enabled and not phoenix_collector_endpoint:
        msg = "PHOENIX_COLLECTOR_ENDPOINT is required when PHOENIX_ENABLED=true."
        raise ValueError(msg)

    return Settings(
        techdocs_mcp_url=techdocs_mcp_url,
        bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "bedrock.nova-lite"),
        playground_config_dir=config_dir,
        conversation_manager=os.getenv("CONVERSATION_MANAGER", "sliding"),
        sliding_window_size=int(os.getenv("SLIDING_WINDOW_SIZE", "12")),
        summary_ratio=float(os.getenv("SUMMARY_RATIO", "0.3")),
        preserve_recent_messages=int(os.getenv("PRESERVE_RECENT_MESSAGES", "10")),
        session_manager=os.getenv("SESSION_MANAGER", "file"),
        session_storage_dir=os.getenv("SESSION_STORAGE_DIR", ".data/sessions"),
        approval_tools=_parse_list(os.getenv("APPROVAL_TOOLS", "")),
        run_mode=os.getenv("RUN_MODE", "quick"),
        single_execution_timeout=float(os.getenv("SINGLE_EXECUTION_TIMEOUT", "120")),
        graph_execution_timeout=float(os.getenv("GRAPH_EXECUTION_TIMEOUT", "300")),
        graph_node_timeout=float(os.getenv("GRAPH_NODE_TIMEOUT", "90")),
        swarm_execution_timeout=float(os.getenv("SWARM_EXECUTION_TIMEOUT", "300")),
        swarm_node_timeout=float(os.getenv("SWARM_NODE_TIMEOUT", "90")),
        swarm_max_handoffs=int(os.getenv("SWARM_MAX_HANDOFFS", "12")),
        swarm_max_iterations=int(os.getenv("SWARM_MAX_ITERATIONS", "12")),
        swarm_preset=os.getenv("SWARM_PRESET", "default"),
        phoenix_enabled=phoenix_enabled,
        phoenix_collector_endpoint=phoenix_collector_endpoint,
        phoenix_grpc_port=int(os.getenv("PHOENIX_GRPC_PORT", "4317")),
        phoenix_project_name=os.getenv("PHOENIX_PROJECT_NAME", "agentic-ai-playground"),
        phoenix_public_url=os.getenv("PHOENIX_PUBLIC_URL") or None,
        online_eval_enabled=os.getenv("ONLINE_EVAL_ENABLED", "false").lower() == "true",
        online_eval_model=os.getenv("ONLINE_EVAL_MODEL", "bedrock.nova-micro"),
        online_eval_temperature=float(os.getenv("ONLINE_EVAL_TEMPERATURE", "0.0")),
        online_eval_max_tokens=int(os.getenv("ONLINE_EVAL_MAX_TOKENS", "256")),
        online_eval_sample_rate=float(os.getenv("ONLINE_EVAL_SAMPLE_RATE", "0.1")),
        should_truncate_tool_results=os.getenv("TRUNCATE_TOOL_RESULTS", "true").lower() == "true",
    )
