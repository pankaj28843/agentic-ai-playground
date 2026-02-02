"""MCP provider configuration schema."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MCPProviderConfig:
    """Configuration for a single MCP provider.

    Attributes:
        id: Unique identifier for the provider (from TOML section name)
        name: Human-readable name
        description: What this provider does
        url: Resolved URL for the MCP server
        enabled: Whether this provider is active
        headers: Optional HTTP headers for authentication
    """

    id: str
    name: str
    description: str
    url: str
    enabled: bool = True
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure URL has trailing slash (required by MCP streamable HTTP transport)."""
        if self.url and not self.url.endswith("/"):
            object.__setattr__(self, "url", self.url + "/")
