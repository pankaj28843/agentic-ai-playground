"""Model provider registry for multi-provider support."""

from __future__ import annotations

import logging
import os
import tomllib
from typing import TYPE_CHECKING, Any

from strands.models import BedrockModel

from agent_toolkit.config.config_paths import get_all_config_paths
from agent_toolkit.models.config import ModelConfig, ProviderConfig

if TYPE_CHECKING:
    from pathlib import Path

    from strands.models.model import Model

logger = logging.getLogger(__name__)

# Global registry instance
_default_registry: ModelProviderRegistry | None = None


class ModelProviderRegistry:
    """Registry for model providers and their models.

    Supports declarative configuration of multiple model providers (Bedrock, Anthropic,
    OpenAI, etc.) with named models that can be referenced in agent profiles.

    Model references use the format: "provider.model_name" (e.g., "bedrock.nova-pro")
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._providers: dict[str, ProviderConfig] = {}
        self._default_provider: str | None = None

    def register_provider(self, name: str, config: ProviderConfig) -> None:
        """Register a model provider.

        Args:
            name: Provider name (e.g., "bedrock", "anthropic")
            config: Provider configuration
        """
        self._providers[name] = config
        if config.default:
            self._default_provider = name
        logger.debug("Registered provider: %s (%s)", name, config.type)

    def get_provider(self, name: str) -> ProviderConfig | None:
        """Get a provider by name."""
        return self._providers.get(name)

    def get_default_provider(self) -> str | None:
        """Get the name of the default provider."""
        return self._default_provider

    def list_providers(self) -> list[str]:
        """List all registered provider names."""
        return list(self._providers.keys())

    def list_models(self, provider_name: str | None = None) -> list[str]:
        """List all registered models, optionally filtered by provider.

        Args:
            provider_name: If provided, only list models from this provider.
                          Returns empty list if provider doesn't exist.

        Returns:
            Model references in "provider.model_name" format.
        """
        if provider_name is not None:
            if provider_name not in self._providers:
                return []
            providers = [(provider_name, self._providers[provider_name])]
        else:
            providers = list(self._providers.items())

        return [
            f"{prov_name}.{model_name}"
            for prov_name, prov_config in providers
            for model_name in prov_config.models
        ]

    def resolve_model_id(self, reference: str) -> tuple[str, str, ModelConfig]:
        """Resolve a model reference to provider, model_id, and config.

        Args:
            reference: Model reference in "provider.model_name" format,
                      or just "model_name" to use default provider,
                      or a raw model_id (e.g., "us.amazon.nova-pro-v1:0")

        Returns:
            Tuple of (provider_name, model_id, model_config)

        Raises:
            ValueError: If model reference cannot be resolved
        """
        # Known raw Bedrock model ID prefixes (vendor prefixes used by AWS)
        raw_model_prefixes = (
            "us.",
            "eu.",
            "amazon.",
            "cohere.",
            "meta.",
            "mistral.",
            "ai21.",
            "stability.",
        )
        # Note: "anthropic." is NOT in raw_model_prefixes because we want
        # "anthropic.claude" (our provider) to take precedence over
        # "anthropic.claude-v2:1" (Bedrock model). Raw Bedrock anthropic models
        # should use the full ID like "anthropic.claude-3-5-sonnet-20240620-v1:0"

        # Check if it's a provider.model reference first
        # This takes priority over raw model ID detection
        if "." in reference:
            parts = reference.split(".", 1)
            if len(parts) == 2:
                provider_name, model_name = parts
                # If provider is registered, use it
                if provider_name in self._providers:
                    provider = self._providers[provider_name]
                    if model_name in provider.models:
                        model_config = provider.models[model_name]
                        return provider_name, model_config.model_id, model_config
                    msg = f"Unknown model '{model_name}' in provider '{provider_name}'"
                    raise ValueError(msg)
                # Provider not registered - check if it looks like a raw model ID
                if reference.startswith(raw_model_prefixes):
                    pass  # Fall through to raw model_id handling
                # else: Unknown provider, not a raw model ID pattern - fall through

        # Try default provider
        if self._default_provider:
            provider = self._providers[self._default_provider]
            if reference in provider.models:
                model_config = provider.models[reference]
                return self._default_provider, model_config.model_id, model_config

        # Treat as raw model_id - create synthetic config
        logger.debug("Treating '%s' as raw model_id", reference)
        default_config = ModelConfig(model_id=reference)
        provider_name = self._default_provider or "bedrock"
        return provider_name, reference, default_config

    def create_model(self, reference: str, *, overrides: dict[str, Any] | None = None) -> Model:
        """Create a model instance from a reference.

        Args:
            reference: Model reference (e.g., "bedrock.nova-pro", "nova-lite", or raw model_id)
            overrides: Optional config overrides (temperature, max_tokens, streaming)

        Returns:
            Configured model instance
        """
        provider_name, model_id, model_config = self.resolve_model_id(reference)
        provider = self._providers.get(provider_name)

        # Apply overrides to model config
        effective_config = self.apply_overrides(model_config, overrides)

        if provider is None or provider.type == "bedrock":
            # Default to Bedrock
            region = provider.region if provider and provider.region else "eu-central-1"
            return BedrockModel(
                model_id=model_id,
                region_name=region,
                temperature=effective_config.temperature,
                max_tokens=effective_config.max_tokens,
                streaming=effective_config.streaming,
            )

        if provider.type == "anthropic":
            return self._create_anthropic_model(provider, effective_config)

        if provider.type == "openai":
            return self._create_openai_model(provider, effective_config)

        if provider.type == "ollama":
            return self._create_ollama_model(provider, effective_config)

        # Unknown provider type - fail fast with clear error
        supported_types = ["bedrock", "anthropic", "openai", "ollama"]
        msg = f"Unsupported provider type '{provider.type}'. Supported types: {supported_types}"
        raise ValueError(msg)

    def apply_overrides(self, config: ModelConfig, overrides: dict[str, Any] | None) -> ModelConfig:
        """Apply overrides to a model config, returning a new config."""
        if not overrides:
            return config

        return ModelConfig(
            model_id=config.model_id,
            temperature=overrides.get("temperature", config.temperature),
            max_tokens=overrides.get("max_tokens", config.max_tokens),
            streaming=overrides.get("streaming", config.streaming),
            extra={**config.extra, **overrides.get("extra", {})},
        )

    def _create_anthropic_model(self, provider: ProviderConfig, model_config: ModelConfig) -> Model:
        """Create an Anthropic model instance."""
        from strands.models.anthropic import AnthropicModel  # noqa: PLC0415

        api_key = os.getenv(provider.api_key_env or "ANTHROPIC_API_KEY")
        if not api_key:
            msg = f"Missing API key: set {provider.api_key_env or 'ANTHROPIC_API_KEY'}"
            raise ValueError(msg)

        return AnthropicModel(
            model_id=model_config.model_id,
            client_args={"api_key": api_key},
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
        )

    def _create_openai_model(self, provider: ProviderConfig, model_config: ModelConfig) -> Model:
        """Create an OpenAI model instance."""
        from strands.models.openai import OpenAIModel  # noqa: PLC0415

        api_key = os.getenv(provider.api_key_env or "OPENAI_API_KEY")
        if not api_key:
            msg = f"Missing API key: set {provider.api_key_env or 'OPENAI_API_KEY'}"
            raise ValueError(msg)

        return OpenAIModel(
            model_id=model_config.model_id,
            client_args={"api_key": api_key},
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
        )

    def _create_ollama_model(self, provider: ProviderConfig, model_config: ModelConfig) -> Model:
        """Create an Ollama model instance."""
        from strands.models.ollama import OllamaModel  # noqa: PLC0415

        host = provider.extra.get("host")
        if not host:
            msg = "Ollama provider requires extra.host (example: http://ollama:11434)."
            raise ValueError(msg)
        return OllamaModel(
            host=host,
            model_id=model_config.model_id,
            temperature=model_config.temperature,
        )


def _load_toml_file(path: Path) -> dict[str, Any]:
    """Load TOML file, return empty dict if not found."""
    from pathlib import Path as PathClass  # noqa: PLC0415

    if isinstance(path, str):
        path = PathClass(path)
    if not path.exists():
        return {}
    with path.open("rb") as file:
        return tomllib.load(file)


def load_providers() -> ModelProviderRegistry:
    """Load model providers from configuration files.

    Loads from config/providers.toml. If PLAYGROUND_CONFIG_DIR is set,
    loads from that location instead (external config replaces bundled).

    Returns:
        ModelProviderRegistry with loaded providers, or empty registry with
        warning if no providers.toml found.
    """
    registry = ModelProviderRegistry()
    paths = get_all_config_paths("providers")

    if not paths:
        logger.warning(
            "No providers.toml found. Model references like 'bedrock.nova-lite' "
            "will fail. Create config/providers.toml or set PLAYGROUND_CONFIG_DIR."
        )
        return registry

    for path in paths:
        data = _load_toml_file(path)
        providers_data = data.get("providers", {})

        for name, config in providers_data.items():
            # Parse models
            models: dict[str, ModelConfig] = {}
            models_data = config.get("models", {})
            for model_name, model_data in models_data.items():
                model_id = model_data.get("model_id")
                if not model_id:
                    msg = f"Missing model_id for model '{model_name}' in provider '{name}'"
                    raise ValueError(msg)
                models[model_name] = ModelConfig(
                    model_id=str(model_id),
                    temperature=float(model_data.get("temperature", 0.7)),
                    max_tokens=model_data.get("max_tokens"),
                    streaming=bool(model_data.get("streaming", True)),
                    extra=dict(model_data.get("extra", {})),
                )

            provider_config = ProviderConfig(
                type=str(config.get("type", "bedrock")),
                region=config.get("region"),
                api_key_env=config.get("api_key_env"),
                default=bool(config.get("default", False)),
                models=models,
                extra=dict(config.get("extra", {})),
            )
            registry.register_provider(name, provider_config)

    logger.info(
        "Loaded %d model providers with %d total models",
        len(registry.list_providers()),
        len(registry.list_models()),
    )
    return registry


def get_default_registry() -> ModelProviderRegistry:
    """Get or create the default model provider registry."""
    global _default_registry  # noqa: PLW0603
    if _default_registry is None:
        _default_registry = load_providers()
    return _default_registry
