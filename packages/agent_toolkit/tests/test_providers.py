"""Tests for the model provider registry."""

from unittest.mock import MagicMock, patch

import pytest
from agent_toolkit.models.config import ModelConfig, ProviderConfig
from agent_toolkit.providers.registry import ModelProviderRegistry


class TestModelProviderRegistry:
    """Tests for ModelProviderRegistry."""

    @pytest.fixture
    def registry(self) -> ModelProviderRegistry:
        """Create a registry with test providers."""
        reg = ModelProviderRegistry()

        # Register Bedrock provider
        bedrock_provider = ProviderConfig(
            type="bedrock",
            region="eu-central-1",
            default=True,
            models={
                "nova-pro": ModelConfig(
                    model_id="us.amazon.nova-pro-v1:0",
                    temperature=0.7,
                    max_tokens=8000,
                ),
                "nova-lite": ModelConfig(
                    model_id="us.amazon.nova-lite-v1:0",
                    temperature=0.5,
                ),
            },
        )
        reg.register_provider("bedrock", bedrock_provider)

        return reg

    def test_register_provider(self, registry: ModelProviderRegistry) -> None:
        """Test provider registration."""
        assert "bedrock" in registry.list_providers()
        assert registry.get_default_provider() == "bedrock"

    def test_list_models(self, registry: ModelProviderRegistry) -> None:
        """Test listing models."""
        models = registry.list_models()
        assert "bedrock.nova-pro" in models
        assert "bedrock.nova-lite" in models

    def test_list_models_by_provider(self, registry: ModelProviderRegistry) -> None:
        """Test listing models filtered by provider."""
        models = registry.list_models("bedrock")
        assert len(models) == 2
        assert all(m.startswith("bedrock.") for m in models)

    def test_resolve_model_id_with_provider_prefix(self, registry: ModelProviderRegistry) -> None:
        """Test resolving model with provider.model format."""
        provider, model_id, config = registry.resolve_model_id("bedrock.nova-pro")
        assert provider == "bedrock"
        assert model_id == "us.amazon.nova-pro-v1:0"
        assert config.temperature == 0.7

    def test_resolve_model_id_default_provider(self, registry: ModelProviderRegistry) -> None:
        """Test resolving model using default provider."""
        provider, model_id, _ = registry.resolve_model_id("nova-lite")
        assert provider == "bedrock"
        assert model_id == "us.amazon.nova-lite-v1:0"

    def test_resolve_model_id_raw_model_id(self, registry: ModelProviderRegistry) -> None:
        """Test resolving raw model_id."""
        provider, model_id, _ = registry.resolve_model_id("anthropic.claude-sonnet-4-20250514-v1:0")
        # Raw model_id should be passed through with default bedrock provider
        assert provider == "bedrock"
        assert model_id == "anthropic.claude-sonnet-4-20250514-v1:0"

    @patch("agent_toolkit.providers.registry.BedrockModel")
    def test_create_model_bedrock(
        self, mock_bedrock: MagicMock, registry: ModelProviderRegistry
    ) -> None:
        """Test creating a Bedrock model."""
        mock_bedrock.return_value = MagicMock(name="bedrock_model")

        model = registry.create_model("bedrock.nova-pro")

        mock_bedrock.assert_called_once_with(
            model_id="us.amazon.nova-pro-v1:0",
            region_name="eu-central-1",
            temperature=0.7,
            max_tokens=8000,
            streaming=True,
        )
        assert model is not None

    def test_create_model_unknown_provider_falls_through(
        self, registry: ModelProviderRegistry
    ) -> None:
        """Test that unknown provider name falls through to raw model_id handling."""
        with patch("agent_toolkit.providers.registry.BedrockModel") as mock_bedrock:
            mock_bedrock.return_value = MagicMock()
            # "unknown.model-xyz" - unknown provider, falls through to raw model_id
            registry.create_model("unknown.model-xyz")
            mock_bedrock.assert_called_once()

    def test_create_model_known_provider_unknown_model_raises(
        self, registry: ModelProviderRegistry
    ) -> None:
        """Test that known provider with unknown model raises ValueError."""
        with pytest.raises(ValueError, match="Unknown model 'nonexistent'"):
            registry.create_model("bedrock.nonexistent")

    def test_create_model_raw_model_id_fallback(self, registry: ModelProviderRegistry) -> None:
        """Test that raw model IDs fall back to default provider."""
        with patch("agent_toolkit.providers.registry.BedrockModel") as mock_bedrock:
            mock_bedrock.return_value = MagicMock()
            registry.create_model("us.amazon.custom-model-v1:0")
            # Should fall back to Bedrock with raw model_id
            mock_bedrock.assert_called_once()


class TestMultipleProviders:
    """Tests for multiple provider support."""

    @pytest.fixture
    def multi_registry(self) -> ModelProviderRegistry:
        """Create registry with multiple providers."""
        reg = ModelProviderRegistry()

        # Add Bedrock as default provider
        reg.register_provider(
            "bedrock",
            ProviderConfig(
                type="bedrock",
                region="eu-central-1",
                default=True,
                models={"nova": ModelConfig(model_id="us.amazon.nova-pro-v1:0")},
            ),
        )

        # Anthropic (not installed, so tests won't actually create)
        reg.register_provider(
            "anthropic",
            ProviderConfig(
                type="anthropic",
                api_key_env="ANTHROPIC_API_KEY",
                models={"claude-sonnet": ModelConfig(model_id="claude-sonnet-4-20250514")},
            ),
        )

        return reg

    def test_list_all_providers(self, multi_registry: ModelProviderRegistry) -> None:
        """Test listing all providers."""
        providers = multi_registry.list_providers()
        assert "bedrock" in providers
        assert "anthropic" in providers

    def test_list_all_models(self, multi_registry: ModelProviderRegistry) -> None:
        """Test listing models from all providers."""
        models = multi_registry.list_models()
        assert "bedrock.nova" in models
        assert "anthropic.claude-sonnet" in models

    def test_resolve_specific_provider(self, multi_registry: ModelProviderRegistry) -> None:
        """Test resolving model from specific non-Bedrock provider."""
        # Use OpenAI as it doesn't collide with raw model_id patterns
        multi_registry.register_provider(
            "openai",
            ProviderConfig(
                type="openai",
                api_key_env="OPENAI_API_KEY",
                models={"gpt-4": ModelConfig(model_id="gpt-4-turbo")},
            ),
        )
        provider, model_id, _ = multi_registry.resolve_model_id("openai.gpt-4")
        assert provider == "openai"
        assert model_id == "gpt-4-turbo"


class TestModelConfigOverrides:
    """Tests for model config overrides."""

    @pytest.fixture
    def registry(self) -> ModelProviderRegistry:
        """Create a registry with test providers."""
        reg = ModelProviderRegistry()
        reg.register_provider(
            "bedrock",
            ProviderConfig(
                type="bedrock",
                region="eu-central-1",
                default=True,
                models={
                    "nova-pro": ModelConfig(
                        model_id="us.amazon.nova-pro-v1:0",
                        temperature=0.7,
                        max_tokens=8000,
                    ),
                },
            ),
        )
        return reg

    @patch("agent_toolkit.providers.registry.BedrockModel")
    def test_overrides_applied(
        self, mock_bedrock: MagicMock, registry: ModelProviderRegistry
    ) -> None:
        """Test that overrides are applied to model config."""
        mock_bedrock.return_value = MagicMock()

        registry.create_model(
            "bedrock.nova-pro", overrides={"temperature": 0.9, "max_tokens": 16000}
        )

        mock_bedrock.assert_called_once_with(
            model_id="us.amazon.nova-pro-v1:0",
            region_name="eu-central-1",
            temperature=0.9,
            max_tokens=16000,
            streaming=True,
        )

    def test_apply_overrides_method(self, registry: ModelProviderRegistry) -> None:
        """Test apply_overrides method directly."""
        base_config = ModelConfig(
            model_id="test-model",
            temperature=0.5,
            max_tokens=1000,
        )

        result = registry.apply_overrides(base_config, {"temperature": 0.8})

        assert result.temperature == 0.8
        assert result.max_tokens == 1000
        assert result.model_id == "test-model"

    def test_no_overrides_returns_original(self, registry: ModelProviderRegistry) -> None:
        """Test that None overrides returns original config."""
        base_config = ModelConfig(model_id="test-model", temperature=0.5)
        result = registry.apply_overrides(base_config, None)
        assert result is base_config


class TestNonBedrockProviders:
    """Tests for non-Bedrock provider creation paths."""

    @pytest.fixture
    def registry(self) -> ModelProviderRegistry:
        """Create registry with multiple provider types."""
        reg = ModelProviderRegistry()
        reg.register_provider(
            "anthropic",
            ProviderConfig(
                type="anthropic",
                api_key_env="ANTHROPIC_API_KEY",
                models={"claude": ModelConfig(model_id="claude-sonnet-4-20250514")},
            ),
        )
        reg.register_provider(
            "openai",
            ProviderConfig(
                type="openai",
                api_key_env="OPENAI_API_KEY",
                models={"gpt-4": ModelConfig(model_id="gpt-4-turbo")},
            ),
        )
        reg.register_provider(
            "ollama",
            ProviderConfig(
                type="ollama",
                models={"llama": ModelConfig(model_id="llama3.2")},
                extra={"host": "http://ollama:11434"},
            ),
        )
        return reg

    def test_anthropic_missing_api_key_raises(self, registry: ModelProviderRegistry) -> None:
        """Test that missing Anthropic API key raises ValueError."""
        import os
        import sys

        env_backup = os.environ.get("ANTHROPIC_API_KEY")
        os.environ.pop("ANTHROPIC_API_KEY", None)

        # Mock the module to allow import
        mock_module = MagicMock()
        mock_module.AnthropicModel = MagicMock()

        try:
            with (
                patch.dict(sys.modules, {"strands.models.anthropic": mock_module}),
                pytest.raises(ValueError, match=r"Missing API key.*ANTHROPIC_API_KEY"),
            ):
                registry.create_model("anthropic.claude")
        finally:
            if env_backup:
                os.environ["ANTHROPIC_API_KEY"] = env_backup

    def test_openai_missing_api_key_raises(self, registry: ModelProviderRegistry) -> None:
        """Test that missing OpenAI API key raises ValueError."""
        import os
        import sys

        env_backup = os.environ.get("OPENAI_API_KEY")
        os.environ.pop("OPENAI_API_KEY", None)

        # Mock the module to allow import
        mock_module = MagicMock()
        mock_module.OpenAIModel = MagicMock()

        try:
            with (
                patch.dict(sys.modules, {"strands.models.openai": mock_module}),
                pytest.raises(ValueError, match=r"Missing API key.*OPENAI_API_KEY"),
            ):
                registry.create_model("openai.gpt-4")
        finally:
            if env_backup:
                os.environ["OPENAI_API_KEY"] = env_backup

    def test_anthropic_model_created_with_api_key(self, registry: ModelProviderRegistry) -> None:
        """Test Anthropic model creation with API key."""
        import os
        import sys

        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        mock_module = MagicMock()
        mock_anthropic = MagicMock()
        mock_module.AnthropicModel = mock_anthropic

        try:
            with patch.dict(sys.modules, {"strands.models.anthropic": mock_module}):
                registry.create_model("anthropic.claude")
                mock_anthropic.assert_called_once()
                call_kwargs = mock_anthropic.call_args[1]
                assert call_kwargs["model_id"] == "claude-sonnet-4-20250514"
        finally:
            os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_ollama_model_created_without_api_key(self, registry: ModelProviderRegistry) -> None:
        """Test Ollama model creation (no API key required)."""
        import sys

        mock_module = MagicMock()
        mock_ollama = MagicMock()
        mock_module.OllamaModel = mock_ollama

        with patch.dict(sys.modules, {"strands.models.ollama": mock_module}):
            registry.create_model("ollama.llama")
            mock_ollama.assert_called_once()
            call_kwargs = mock_ollama.call_args[1]
            assert call_kwargs["model_id"] == "llama3.2"
            assert call_kwargs["host"] == "http://ollama:11434"

    def test_unsupported_provider_type_raises(self, registry: ModelProviderRegistry) -> None:
        """Test that unsupported provider type raises ValueError."""
        registry.register_provider(
            "custom",
            ProviderConfig(
                type="unsupported_type",
                models={"model": ModelConfig(model_id="custom-model")},
            ),
        )
        with pytest.raises(ValueError, match="Unsupported provider type"):
            registry.create_model("custom.model")
