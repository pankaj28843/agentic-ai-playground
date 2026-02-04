"""MCP provider registry - loads providers from TOML configuration.

This module provides a generic factory for creating MCP clients from
configuration, eliminating the need for provider-specific code.

Usage:
    from agent_toolkit.mcp.registry import get_provider, get_client, list_providers

    # Get a specific provider's client
    client = get_client("techdocs")

    # List all enabled providers
    providers = list_providers()
"""

from __future__ import annotations

import json
import logging
import os
import tomllib
from pathlib import Path  # noqa: TC003 (needed at runtime)

from mcp.client.streamable_http import streamable_http_client
from strands.tools.mcp import MCPClient

from agent_toolkit.config.config_paths import resolve_config_path
from agent_toolkit.mcp.config import MCPProviderConfig
from agent_toolkit.mcp.resilient_client import ResilientMCPClient

logger = logging.getLogger(__name__)


class MCPProviderRegistry:
    """Registry for MCP providers loaded from TOML configuration.

    Providers are loaded lazily on first access. Each provider can create
    fresh MCPClient instances for use with Strands Agent.

    The registry is a singleton - use get_registry() to access it.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize registry with optional config path override."""
        self._config_path = config_path
        self._providers: dict[str, MCPProviderConfig] | None = None
        self._clients: dict[str, MCPClient] = {}

    def _get_config_path(self) -> Path:
        """Get the config path, resolving from unified config paths if not explicitly set."""
        if self._config_path:
            return self._config_path
        return resolve_config_path("mcp_providers")

    def _load_config(self) -> dict[str, MCPProviderConfig]:
        """Load provider configurations from TOML file."""
        config_path = self._get_config_path()
        if not config_path.exists():
            logger.warning("MCP config not found at %s", config_path)
            return {}

        with config_path.open("rb") as f:
            raw_config = tomllib.load(f)

        providers: dict[str, MCPProviderConfig] = {}
        for provider_id, config in raw_config.items():
            try:
                provider = self._parse_provider(provider_id, config)
                if provider.enabled and provider.url:
                    providers[provider_id] = provider
                    logger.debug("Loaded MCP provider: %s (%s)", provider_id, provider.url)
                elif not provider.enabled:
                    logger.debug("Skipping disabled provider: %s", provider_id)
            except Exception:
                logger.exception("Failed to parse provider config: %s", provider_id)

        logger.info("Loaded %d MCP providers: %s", len(providers), list(providers.keys()))
        return providers

    def _parse_provider(self, provider_id: str, config: dict) -> MCPProviderConfig:
        """Parse a single provider configuration."""
        # Resolve URL from environment or default
        url_env = config.get("url_env", "")
        url_default = config.get("url_default", "")
        url = os.getenv(url_env, "") if url_env else ""
        if not url:
            url = url_default

        # Resolve optional headers from environment
        headers: dict[str, str] = {}
        headers_env = config.get("headers_env", "")
        if headers_env:
            headers_json = os.getenv(headers_env, "")
            if headers_json:
                try:
                    headers = json.loads(headers_json)
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in %s for provider %s", headers_env, provider_id)

        return MCPProviderConfig(
            id=provider_id,
            name=config.get("name", provider_id),
            description=config.get("description", ""),
            url=url,
            enabled=config.get("enabled", True),
            headers=headers,
        )

    @property
    def providers(self) -> dict[str, MCPProviderConfig]:
        """Get all loaded provider configurations (lazy load)."""
        if self._providers is None:
            self._providers = self._load_config()
        return self._providers

    def get_provider(self, provider_id: str) -> MCPProviderConfig | None:
        """Get a specific provider configuration by ID."""
        return self.providers.get(provider_id)

    def get_client(
        self, provider_id: str, *, resilient: bool = True
    ) -> MCPClient | ResilientMCPClient:
        """Create a fresh MCPClient for the specified provider.

        Returns a new client each time - Strands manages the lifecycle.
        The client is passed directly to Agent(tools=[client]).

        Args:
            provider_id: The provider identifier (e.g., "techdocs")
            resilient: If True (default), wrap client with retry/reconnect logic.
                      Set to False for direct MCPClient access (e.g., testing).

        Raises:
            ValueError: If provider not found or not configured
        """
        provider = self.get_provider(provider_id)
        if not provider:
            msg = f"MCP provider not found: {provider_id}"
            raise ValueError(msg)

        if not provider.url:
            msg = f"MCP provider {provider_id} has no URL configured"
            raise ValueError(msg)

        logger.info(
            "Creating MCPClient for %s (%s) [resilient=%s]", provider_id, provider.url, resilient
        )

        # Use provider name as tool prefix to avoid conflicts between MCP servers
        tool_prefix = provider.name

        # Create transport factory with optional headers
        if provider.headers:

            def transport_factory(
                url: str = provider.url, headers: dict = provider.headers
            ) -> streamable_http_client:
                return streamable_http_client(url, headers=headers)

        else:

            def transport_factory(url: str = provider.url) -> streamable_http_client:
                return streamable_http_client(url)

        # Factory for creating MCPClient instances
        def client_factory() -> MCPClient:
            return MCPClient(transport_factory, prefix=tool_prefix)

        if resilient:
            return ResilientMCPClient(
                client_factory=client_factory,
                provider_name=provider_id,
                max_retries=3,
                initial_delay=1.0,
                max_delay=30.0,
            )

        return client_factory()

    def list_providers(self) -> list[MCPProviderConfig]:
        """List all enabled provider configurations."""
        return list(self.providers.values())

    def list_tools(self, provider_id: str) -> list[dict]:
        """List available tools from a provider's MCP server.

        Useful for validation and debugging.
        """
        client = self.get_client(provider_id)
        try:
            with client:
                tools = client.list_tools_sync()
                return [
                    {
                        "name": getattr(t, "name", str(t)),
                        "description": getattr(t, "description", ""),
                    }
                    for t in tools
                ]
        except Exception:
            logger.exception("Failed to list tools from %s", provider_id)
            return []

    def validate(self, provider_id: str) -> bool:
        """Validate that a provider's MCP server is reachable and has tools."""
        try:
            tools = self.list_tools(provider_id)
            return len(tools) > 0
        except Exception:
            logger.exception("Validation failed for %s", provider_id)
            return False

    def reset(self) -> None:
        """Reset the registry (clears cached providers)."""
        self._providers = None
        self._clients.clear()


# Module-level singleton registry
_registry: MCPProviderRegistry | None = None


def get_registry(config_path: Path | None = None) -> MCPProviderRegistry:
    """Get the singleton MCP provider registry.

    Args:
        config_path: Optional path to TOML config file (only used on first call)
    """
    global _registry  # noqa: PLW0603
    if _registry is None:
        _registry = MCPProviderRegistry(config_path)
    return _registry


def get_provider(provider_id: str) -> MCPProviderConfig | None:
    """Get a specific provider configuration."""
    return get_registry().get_provider(provider_id)


def get_client(provider_id: str, *, resilient: bool = True) -> MCPClient | ResilientMCPClient:
    """Get a fresh MCPClient for the specified provider.

    Args:
        provider_id: The provider identifier (e.g., "techdocs")
        resilient: If True (default), wrap client with retry/reconnect logic.

    Returns:
        MCPClient or ResilientMCPClient depending on resilient flag.
    """
    return get_registry().get_client(provider_id, resilient=resilient)


def list_providers() -> list[MCPProviderConfig]:
    """List all enabled providers."""
    return get_registry().list_providers()


def reset_registry() -> None:
    """Reset the registry (useful for testing)."""
    global _registry  # noqa: PLW0603
    if _registry:
        _registry.reset()
    _registry = None
