"""Phoenix telemetry provider for LLM observability.

This module integrates Arize Phoenix for comprehensive agent telemetry,
including trace visualization, token usage tracking, and latency analysis.
"""

from __future__ import annotations

import logging
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from opentelemetry import trace as otel_trace
from opentelemetry.trace import Status, StatusCode, format_trace_id

if TYPE_CHECKING:
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import Span

logger = logging.getLogger(__name__)


@dataclass
class SessionTurnContext:
    """Context for a single session turn with Phoenix telemetry."""

    session_id: str
    run_mode: str
    input_value: str
    profile_name: str | None = None
    thread_id: str | None = None
    message_id: str | None = None
    execution_mode: str | None = None
    entrypoint_reference: str | None = None
    trace_id: str | None = None
    _span: Span | None = field(default=None, repr=False)

    @contextmanager
    def span(self):
        """Create a Phoenix session turn span.

        Yields the span and captures the trace ID for later use.
        """
        tracer = otel_trace.get_tracer("agent_toolkit.session")
        attributes: dict[str, Any] = {
            "openinference.span.kind": "CHAIN",
            "session.id": self.session_id,
            "run.mode": self.run_mode,
            "input.value": self.input_value,
        }
        if self.profile_name:
            attributes["agent.profile"] = self.profile_name
        if self.thread_id:
            attributes["thread.id"] = self.thread_id
        if self.message_id:
            attributes["message.id"] = self.message_id
        if self.execution_mode:
            attributes["run.execution_mode"] = self.execution_mode
        if self.entrypoint_reference:
            attributes["run.entrypoint"] = self.entrypoint_reference

        with tracer.start_as_current_span("session_turn", attributes=attributes) as span:
            self._span = span
            # Capture trace ID
            ctx = span.get_span_context()
            if ctx.trace_id != 0:
                self.trace_id = format_trace_id(ctx.trace_id)
                logger.debug("Captured Phoenix trace_id: %s", self.trace_id)
            try:
                yield span
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def set_output(self, output: str) -> None:
        """Set the output value on the span."""
        if self._span:
            self._span.set_attribute("output.value", output)
            self._span.set_status(Status(StatusCode.OK))

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        """Add a span event with optional attributes."""
        if self._span:
            self._span.add_event(name, attributes or {})


def get_current_trace_id() -> str | None:
    """Get the current OpenTelemetry trace ID if available."""
    try:
        span = otel_trace.get_current_span()
        if span is None:
            return None
        ctx = span.get_span_context()
        if ctx.trace_id == 0:
            return None
        return format_trace_id(ctx.trace_id)
    except Exception:  # noqa: BLE001
        return None


@dataclass
class PhoenixConfig:
    """Configuration for Phoenix telemetry."""

    enabled: bool
    collector_endpoint: str
    grpc_port: int
    project_name: str

    @classmethod
    def from_settings(cls, settings: Any) -> PhoenixConfig:
        """Create config from Settings dataclass."""
        return cls(
            enabled=settings.phoenix_enabled,
            collector_endpoint=settings.phoenix_collector_endpoint,
            grpc_port=settings.phoenix_grpc_port,
            project_name=settings.phoenix_project_name,
        )


class PhoenixTelemetryProvider:
    """Phoenix telemetry provider for LLM observability.

    This provider configures OpenTelemetry to export traces to Phoenix,
    enabling trace visualization, token usage tracking, and latency analysis.
    """

    def __init__(self, config: PhoenixConfig) -> None:
        """Initialize the Phoenix telemetry provider.

        Args:
            config: Phoenix configuration settings.
        """
        self._config = config
        self._tracer_provider: TracerProvider | None = None
        self._initialized = False

    @property
    def enabled(self) -> bool:
        """Check if Phoenix telemetry is enabled."""
        return self._config.enabled

    @property
    def initialized(self) -> bool:
        """Check if telemetry has been initialized."""
        return self._initialized

    def setup(self) -> TracerProvider | None:
        """Configure and register the OpenTelemetry tracer provider.

        Returns:
            The configured TracerProvider, or None if setup fails or is disabled.
        """
        if not self._config.enabled:
            logger.debug("Phoenix telemetry is disabled")
            return None

        if self._initialized:
            logger.debug("Phoenix telemetry already initialized")
            return self._tracer_provider

        return self._do_setup()

    def _do_setup(self) -> TracerProvider | None:
        """Internal setup logic with exception handling."""
        try:
            from phoenix.otel import register  # noqa: PLC0415

            # Build the OTLP endpoint (HTTP)
            endpoint = self._config.collector_endpoint
            if not endpoint.endswith("/v1/traces"):
                endpoint = endpoint.rstrip("/") + "/v1/traces"

            logger.info(
                "Setting up Phoenix telemetry: endpoint=%s, project=%s",
                endpoint,
                self._config.project_name,
            )

            # Register Phoenix OTEL with auto-instrumentation
            # This automatically instruments supported frameworks including Bedrock
            self._tracer_provider = register(
                project_name=self._config.project_name,
                endpoint=endpoint,
                auto_instrument=True,
            )
            self._initialized = True

            logger.info("Phoenix telemetry initialized successfully")
        except ImportError as e:
            logger.warning("Phoenix OTEL not available: %s", e)
        except OSError as e:
            logger.warning("Failed to initialize Phoenix telemetry (connection error): %s", e)
        except RuntimeError as e:
            logger.warning("Failed to initialize Phoenix telemetry (runtime error): %s", e)
        except Exception as e:  # noqa: BLE001
            # Catch any unexpected errors - telemetry failures shouldn't crash the app
            logger.warning("Unexpected error initializing Phoenix telemetry: %s", e)
        return self._tracer_provider

    def get_tracer(self, name: str = __name__) -> Any:
        """Get a tracer for manual instrumentation.

        Args:
            name: Name for the tracer (typically __name__ of the calling module).

        Returns:
            An OpenTelemetry Tracer, or a no-op tracer if not initialized.
        """
        if not self._initialized or self._tracer_provider is None:
            # Return a no-op tracer to avoid breaking code that uses it
            return otel_trace.get_tracer(name)

        return self._tracer_provider.get_tracer(name)

    def shutdown(self) -> None:
        """Shut down the telemetry provider and flush pending spans."""
        if self._tracer_provider is not None:
            try:
                self._tracer_provider.shutdown()
                logger.info("Phoenix telemetry shut down")
            except OSError as e:
                logger.warning("Error shutting down Phoenix telemetry: %s", e)
            finally:
                self._tracer_provider = None
                self._initialized = False

    def build_trace_attributes(
        self,
        *,
        session_id: str = "",
        profile_name: str = "",
        run_mode: str = "",
        thread_id: str = "",
        message_id: str = "",
        execution_mode: str = "",
        entrypoint_reference: str = "",
        **extra: str,
    ) -> dict[str, str]:
        """Build trace attributes for agent context.

        These attributes are added to agent spans for correlation and filtering.

        Args:
            session_id: Session identifier for multi-turn conversations.
            profile_name: Agent profile name.
            run_mode: Public run mode/profile identifier.
            thread_id: Thread identifier for UI correlation.
            message_id: Message identifier for UI correlation.
            execution_mode: Resolved execution mode (single, graph, swarm).
            entrypoint_reference: Reference to the actual entrypoint being executed.
            **extra: Additional custom attributes.

        Returns:
            Dictionary of trace attributes.
        """
        attrs: dict[str, str] = {}
        if session_id:
            attrs["session.id"] = session_id
        if profile_name:
            attrs["agent.profile"] = profile_name
        if run_mode:
            attrs["run.mode"] = run_mode
        if thread_id:
            attrs["thread.id"] = thread_id
        if message_id:
            attrs["message.id"] = message_id
        if execution_mode:
            attrs["run.execution_mode"] = execution_mode
        if entrypoint_reference:
            attrs["run.entrypoint"] = entrypoint_reference
        attrs.update(extra)
        return attrs
