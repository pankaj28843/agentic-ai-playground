"""Agent factory for creating Strands agents from profiles.

The AgentFactory is responsible for:
1. Creating agents from profile configurations (system prompt, tools, model)
2. Resolving tool references from the registry
3. Injecting MCP clients for tool discovery
4. Building specialist sub-agents as callable tools
5. Resolving model references from the provider registry

12-Factor Agents References:
- Factor 2: Own Your Prompts (profiles define system prompts)
- Factor 10: Small, Focused Agents (each profile defines a focused agent)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from agent_toolkit.agents.builders import build_conversation_manager, build_session_manager
from agent_toolkit.config import AgentProfile, Settings
from agent_toolkit.providers import get_default_registry
from agent_toolkit.tools.registry import ToolRegistry, registered_tool

if TYPE_CHECKING:
    from collections.abc import Callable

    from strands import Agent

    from agent_toolkit.providers.registry import ModelProviderRegistry


@dataclass(frozen=True)
class AgentFactory:
    """Factory for constructing Strands agents from profiles or configs."""

    settings: Settings
    registry: ToolRegistry
    model_registry: ModelProviderRegistry | None = None

    def _get_model_registry(self) -> ModelProviderRegistry:
        """Get the model registry, using default if not set."""
        if self.model_registry is not None:
            return self.model_registry
        return get_default_registry()

    def _resolve_model(self, model_ref: str, overrides: dict[str, Any] | None = None) -> Any:
        """Resolve a model reference to a model instance.

        Args:
            model_ref: Model reference (e.g., "bedrock.nova-pro", "nova-lite", or raw model_id)
            overrides: Optional model config overrides (temperature, max_tokens, etc.)

        Returns:
            Model instance (BedrockModel, AnthropicModel, etc.)
        """
        if not model_ref:
            model_ref = self.settings.bedrock_model_id

        registry = self._get_model_registry()
        try:
            return registry.create_model(model_ref, overrides=overrides)
        except ImportError as e:
            # Optional provider not installed - re-raise with helpful message
            msg = f"Cannot create model '{model_ref}': {e}"
            raise ImportError(msg) from e

    def create_from_profile(
        self,
        profile: AgentProfile,
        session_id: str = "",
        *,
        hooks: list[Any] | None = None,
        session_manager: object | None = None,
        conversation_manager: object | None = None,
        use_session_manager: bool = True,
        use_conversation_manager: bool = True,
        trace_attributes: dict[str, str] | None = None,
        mcp_clients: list[Any] | None = None,
    ) -> Agent:
        """Create a Strands agent from a profile configuration.

        Args:
            profile: Agent profile configuration.
            session_id: Session identifier for state persistence.
            hooks: Lifecycle hooks for the agent.
            session_manager: Override session manager (None uses default).
            conversation_manager: Override conversation manager (None uses default).
            use_session_manager: Whether to use session management.
            use_conversation_manager: Whether to use conversation management.
            trace_attributes: Telemetry trace attributes.
            mcp_clients: MCP clients to include as tool providers.
        """
        from strands import Agent  # noqa: PLC0415

        # Start with registry tools
        tools: list[Any] = self.registry.to_strands_tools(profile.tools)

        # Add MCP clients as tool providers (Strands discovers tools automatically)
        if mcp_clients:
            tools.extend(mcp_clients)

        # Resolve model from registry (supports "bedrock.nova-pro" or raw model_id)
        # Apply profile-specific model config overrides if specified
        model = self._resolve_model(
            profile.model or self.settings.bedrock_model_id,
            overrides=profile.model_config_overrides or None,
        )

        resolved_hooks = list(hooks or [])
        if conversation_manager is None and use_conversation_manager:
            conversation_manager = build_conversation_manager(self.settings)
        if session_manager is None and use_session_manager:
            session_manager = build_session_manager(
                self.settings, session_id or f"{profile.name}-session"
            )

        return Agent(
            model=model,
            tools=tools,
            system_prompt=profile.system_prompt,
            name=profile.name,
            description=profile.description,
            hooks=resolved_hooks,
            conversation_manager=conversation_manager,
            session_manager=session_manager,
            trace_attributes=trace_attributes,
        )

    def create_from_config(
        self,
        name: str,
        config: dict[str, Any],
        session_id: str = "",
        *,
        hooks: list[Any] | None = None,
    ) -> Agent:
        """Create a Strands agent from a raw config dict."""
        profile = AgentProfile(
            name=name,
            description=str(config.get("description", "")),
            model=str(config.get("model", "")),
            system_prompt=str(config.get("system_prompt", "")),
            tools=list(config.get("tools", [])),
            tool_groups=list(config.get("tool_groups", [])),
            extends=str(config.get("extends", "")),
            metadata=dict(config.get("metadata", {})),
            constraints=dict(config.get("constraints", {})),
        )
        return self.create_from_profile(
            profile,
            session_id=session_id,
            hooks=hooks,
        )

    def create_specialist_tool_agent(
        self,
        *,
        name: str,
        description: str,
        system_prompt: str,
        tool_names: list[str],
        category: str = "agents",
        tags: tuple[str, ...] = ("specialist",),
        capabilities: tuple[str, ...] = ("delegate",),
    ) -> Callable[[str], str]:
        """Create a specialist sub-agent wrapped as a tool."""

        @registered_tool(
            name=name,
            description=description,
            category=category,
            tags=tags,
            input_schema={
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            output_schema={"type": "string"},
            capabilities=capabilities,
            source=f"agent:{name}",
            registry=self.registry,
        )
        def specialist(query: str) -> str:
            profile = AgentProfile(
                name=name,
                description=description,
                model="",
                system_prompt=system_prompt,
                tools=list(tool_names),
                tool_groups=[],
                extends="",
                metadata={},
                constraints={},
            )
            agent = self.create_from_profile(
                profile,
                session_id=f"{name}-session",
            )
            result = agent(query)
            return (
                getattr(result, "output", None) or getattr(result, "message", None) or str(result)
            )

        return specialist
