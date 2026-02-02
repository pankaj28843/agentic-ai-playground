"""Model provider registry and adapters.

This module provides a registry for model providers (Bedrock, Anthropic, OpenAI, etc.)
that can be configured declaratively in providers.toml and used to create models
for agents.
"""

from agent_toolkit.providers.registry import (
    ModelProviderRegistry,
    get_default_registry,
    load_providers,
)

__all__ = [
    "ModelProviderRegistry",
    "get_default_registry",
    "load_providers",
]
