"""Tests for Phoenix telemetry module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agent_toolkit.telemetry import (
    PhoenixConfig,
    PhoenixTelemetryProvider,
    _telemetry_provider,  # noqa: F401 - for testing global state
    build_trace_attributes,
    setup_telemetry,
    shutdown_telemetry,
)


class TestPhoenixConfig:
    """Tests for PhoenixConfig dataclass."""

    def test_from_settings(self) -> None:
        """Test creating config from settings object."""
        settings = MagicMock()
        settings.phoenix_enabled = True
        settings.phoenix_collector_endpoint = "https://phoenix.example.com"
        settings.phoenix_grpc_port = 4317
        settings.phoenix_project_name = "test-project"

        config = PhoenixConfig.from_settings(settings)

        assert config.enabled is True
        assert config.collector_endpoint == "https://phoenix.example.com"
        assert config.grpc_port == 4317
        assert config.project_name == "test-project"


class TestPhoenixTelemetryProvider:
    """Tests for PhoenixTelemetryProvider."""

    def test_disabled_provider(self) -> None:
        """Test provider when Phoenix is disabled."""
        config = PhoenixConfig(
            enabled=False,
            collector_endpoint="https://phoenix.example.com",
            grpc_port=4317,
            project_name="test",
        )
        provider = PhoenixTelemetryProvider(config)

        assert provider.enabled is False
        assert provider.setup() is None
        assert provider.initialized is False

    def test_enabled_provider_setup(self) -> None:
        """Test provider setup with Phoenix enabled (mocked)."""
        config = PhoenixConfig(
            enabled=True,
            collector_endpoint="https://phoenix.example.com",
            grpc_port=4317,
            project_name="test-project",
        )
        provider = PhoenixTelemetryProvider(config)

        # Mock phoenix register to avoid actual connection
        with patch("agent_toolkit.telemetry.phoenix.register") as mock_register:
            mock_tracer_provider = MagicMock()
            mock_register.return_value = mock_tracer_provider

            result = provider.setup()

            assert result == mock_tracer_provider
            assert provider.initialized is True
            mock_register.assert_called_once_with(
                project_name="test-project",
                endpoint="https://phoenix.example.com/v1/traces",
                auto_instrument=True,
            )

    def test_endpoint_normalization(self) -> None:
        """Test endpoint is normalized to include /v1/traces."""
        config = PhoenixConfig(
            enabled=True,
            collector_endpoint="https://phoenix.example.com/",  # trailing slash
            grpc_port=4317,
            project_name="test",
        )
        provider = PhoenixTelemetryProvider(config)

        with patch("agent_toolkit.telemetry.phoenix.register") as mock_register:
            mock_register.return_value = MagicMock()
            provider.setup()
            mock_register.assert_called_once()
            call_kwargs = mock_register.call_args.kwargs
            assert call_kwargs["endpoint"] == "https://phoenix.example.com/v1/traces"

    def test_build_trace_attributes(self) -> None:
        """Test building trace attributes."""
        config = PhoenixConfig(
            enabled=True,
            collector_endpoint="https://phoenix.example.com",
            grpc_port=4317,
            project_name="test",
        )
        provider = PhoenixTelemetryProvider(config)

        attrs = provider.build_trace_attributes(
            session_id="sess-123",
            profile_name="techdocs",
            run_mode="single",
            custom="value",
        )

        assert attrs["session.id"] == "sess-123"
        assert attrs["agent.profile"] == "techdocs"
        assert attrs["run.mode"] == "single"
        assert attrs["custom"] == "value"

    def test_build_trace_attributes_empty(self) -> None:
        """Test building trace attributes with no values."""
        config = PhoenixConfig(
            enabled=True,
            collector_endpoint="https://phoenix.example.com",
            grpc_port=4317,
            project_name="test",
        )
        provider = PhoenixTelemetryProvider(config)

        attrs = provider.build_trace_attributes()
        assert attrs == {}

    def test_shutdown(self) -> None:
        """Test provider shutdown."""
        config = PhoenixConfig(
            enabled=True,
            collector_endpoint="https://phoenix.example.com",
            grpc_port=4317,
            project_name="test",
        )
        provider = PhoenixTelemetryProvider(config)

        with patch("agent_toolkit.telemetry.phoenix.register") as mock_register:
            mock_tracer_provider = MagicMock()
            mock_register.return_value = mock_tracer_provider

            provider.setup()
            assert provider.initialized is True

            provider.shutdown()
            mock_tracer_provider.shutdown.assert_called_once()
            assert provider.initialized is False


class TestSetupTelemetry:
    """Tests for setup_telemetry function."""

    def teardown_method(self) -> None:
        """Clean up global telemetry state after each test."""
        shutdown_telemetry()

    def test_setup_disabled(self) -> None:
        """Test setup with Phoenix disabled."""
        # First ensure any existing provider is cleared
        shutdown_telemetry()

        settings = MagicMock()
        settings.phoenix_enabled = False
        settings.phoenix_collector_endpoint = "https://phoenix.example.com"
        settings.phoenix_grpc_port = 4317
        settings.phoenix_project_name = "test"

        result = setup_telemetry(settings)
        assert result is None


class TestBuildTraceAttributes:
    """Tests for build_trace_attributes function."""

    def teardown_method(self) -> None:
        """Clean up global telemetry state after each test."""
        shutdown_telemetry()

    def test_build_without_provider(self) -> None:
        """Test building attributes without global provider."""
        # Ensure no provider is set
        shutdown_telemetry()

        attrs = build_trace_attributes(
            session_id="sess-456",
            profile_name="default",
            run_mode="graph",
        )

        assert attrs["session.id"] == "sess-456"
        assert attrs["agent.profile"] == "default"
        assert attrs["run.mode"] == "graph"

    def test_build_empty_without_provider(self) -> None:
        """Test building empty attributes without provider."""
        shutdown_telemetry()
        attrs = build_trace_attributes()
        assert attrs == {}

    def test_build_with_extra_attrs(self) -> None:
        """Test building attributes with extra values."""
        shutdown_telemetry()
        attrs = build_trace_attributes(
            session_id="sess",
            extra_key="extra_value",
        )

        assert attrs["session.id"] == "sess"
        assert attrs["extra_key"] == "extra_value"
