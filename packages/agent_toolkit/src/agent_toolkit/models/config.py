"""Pydantic models for configuration schema."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EntrypointType(str, Enum):
    """Type of execution entrypoint."""

    SINGLE = "single"
    SWARM = "swarm"
    GRAPH = "graph"


class ModelConfig(BaseModel, frozen=True):
    """Configuration for a specific model."""

    model_id: str
    temperature: float = 0.7
    max_tokens: int | None = None
    streaming: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)


class ProviderConfig(BaseModel, frozen=True):
    """Configuration for a model provider."""

    type: str  # bedrock, anthropic, openai, ollama, gemini, etc.
    region: str | None = None
    api_key_env: str | None = None  # Environment variable name for API key
    default: bool = False
    models: dict[str, ModelConfig] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(default_factory=dict)


class ModelProvider(BaseModel, frozen=True):
    """Complete model provider with name."""

    name: str
    config: ProviderConfig


class AtomicAgent(BaseModel, frozen=True):
    """Atomic agent definition - minimal, reusable unit."""

    name: str
    system_prompt: str
    model: str
    tools: list[str] = Field(default_factory=list)
    tool_groups: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    model_config_overrides: dict[str, Any] = Field(
        default_factory=dict,
        alias="model_config",
    )

    model_config = {"populate_by_name": True}


class GraphNode(BaseModel, frozen=True):
    """Node in a graph template."""

    name: str
    agent: str  # Reference to atomic agent


class GraphEdge(BaseModel, frozen=True):
    """Edge in a graph template."""

    from_node: str = Field(alias="from")
    to_node: str = Field(alias="to")

    model_config = {"populate_by_name": True}


class GraphTemplate(BaseModel, frozen=True):
    """Graph orchestration template."""

    name: str
    description: str
    entry_point: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    timeouts: dict[str, int] = Field(default_factory=dict)


class SwarmAgent(BaseModel, frozen=True):
    """Agent reference in a swarm template."""

    name: str
    agent: str  # Reference to atomic agent


class SwarmTemplate(BaseModel, frozen=True):
    """Swarm orchestration template."""

    name: str
    description: str
    entry_point: str
    agents: list[SwarmAgent]
    max_handoffs: int = 10
    max_iterations: int = 15
    timeouts: dict[str, int] = Field(default_factory=dict)


class PublicProfile(BaseModel, frozen=True):
    """Public profile exposed in UI."""

    name: str
    display_name: str
    description: str
    entrypoint_type: EntrypointType
    entrypoint_reference: str
    default: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolGroup(BaseModel, frozen=True):
    """Group of tools that can be referenced by name."""

    name: str
    description: str
    tools: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)


class ConfigSchema(BaseModel, frozen=True):
    """Complete configuration schema."""

    agents: dict[str, AtomicAgent] = Field(default_factory=dict)
    graphs: dict[str, GraphTemplate] = Field(default_factory=dict)
    swarms: dict[str, SwarmTemplate] = Field(default_factory=dict)
    public_profiles: dict[str, PublicProfile] = Field(default_factory=dict)
    tool_groups: dict[str, ToolGroup] = Field(default_factory=dict)
    providers: dict[str, ProviderConfig] = Field(default_factory=dict)


class ValidationResult(BaseModel, frozen=True):
    """Result of configuration validation."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
