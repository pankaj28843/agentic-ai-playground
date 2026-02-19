"""Resilient MCP client wrapper with retry and reconnection logic.

Wraps MCPClient to handle transient failures from MCP server restarts
or network issues, providing automatic retry with exponential backoff.
"""

from __future__ import annotations

import asyncio
import logging
import time
import warnings
from typing import TYPE_CHECKING, Any

# Support both old (experimental) and new (production) import paths
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    try:
        from strands.tools import ToolProvider
    except ImportError:
        from strands.experimental.tools import ToolProvider

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from strands.types.tools import AgentTool

logger = logging.getLogger(__name__)

# Default retry configuration
DEFAULT_MAX_RETRIES = 3
DEFAULT_INITIAL_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 30.0  # seconds
DEFAULT_BACKOFF_MULTIPLIER = 2.0


class ResilientMCPClient(ToolProvider):
    """Wrapper around MCPClient that provides retry and reconnection logic.

    This class wraps an MCPClient and intercepts calls to handle transient
    failures gracefully. When the underlying MCP server restarts or has
    network issues, this wrapper will:

    1. Catch connection/initialization errors
    2. Wait with exponential backoff
    3. Recreate the client and retry

    Implements ToolProvider interface for Strands Agent integration.

    Usage:
        from agent_toolkit.mcp.resilient_client import ResilientMCPClient

        # Wrap your client factory
        resilient = ResilientMCPClient(
            client_factory=lambda: get_client("techdocs"),
            max_retries=3,
        )

        # Use like a normal MCPClient
        agent = Agent(tools=[resilient])
    """

    def __init__(
        self,
        client_factory: Callable[[], Any],
        *,
        max_retries: int = DEFAULT_MAX_RETRIES,
        initial_delay: float = DEFAULT_INITIAL_DELAY,
        max_delay: float = DEFAULT_MAX_DELAY,
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
        provider_name: str = "mcp",
    ) -> None:
        """Initialize the resilient wrapper.

        Args:
            client_factory: Callable that creates a fresh MCPClient instance.
            max_retries: Maximum number of retry attempts.
            initial_delay: Initial delay between retries in seconds.
            max_delay: Maximum delay between retries in seconds.
            backoff_multiplier: Multiplier for exponential backoff.
            provider_name: Name for logging purposes.
        """
        self._client_factory = client_factory
        self._max_retries = max_retries
        self._initial_delay = initial_delay
        self._max_delay = max_delay
        self._backoff_multiplier = backoff_multiplier
        self._provider_name = provider_name
        self._client: Any = None
        self._is_started = False

    def _create_client(self) -> Any:
        """Create a fresh MCPClient instance."""
        return self._client_factory()

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for exponential backoff."""
        delay = self._initial_delay * (self._backoff_multiplier**attempt)
        return min(delay, self._max_delay)

    def _with_retry(self, operation: Callable[[], Any], operation_name: str) -> Any:
        """Execute an operation with retry logic.

        Args:
            operation: The operation to execute.
            operation_name: Name for logging.

        Returns:
            Result of the operation.

        Raises:
            Exception: If all retries are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                return operation()
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()

                # Check if this is a retryable error
                is_retryable = any(
                    phrase in error_msg
                    for phrase in [
                        "failed to start",
                        "initialization failed",
                        "connection refused",
                        "connection reset",
                        "timeout",
                        "temporarily unavailable",
                        "server disconnected",
                        "broken pipe",
                        "network",
                    ]
                )

                if not is_retryable or attempt >= self._max_retries:
                    logger.exception(
                        "MCP %s operation '%s' failed after %d attempts",
                        self._provider_name,
                        operation_name,
                        attempt + 1,
                    )
                    raise

                delay = self._calculate_delay(attempt)
                logger.warning(
                    "MCP %s operation '%s' failed (attempt %d/%d), retrying in %.1fs: %s",
                    self._provider_name,
                    operation_name,
                    attempt + 1,
                    self._max_retries + 1,
                    delay,
                    e,
                )
                time.sleep(delay)

                # Reset client for next attempt
                self._cleanup_client()
                self._client = None

        # Should not reach here, but just in case
        if last_error:
            raise last_error
        msg = f"MCP {self._provider_name} operation failed unexpectedly"
        raise RuntimeError(msg)

    def _cleanup_client(self) -> None:
        """Clean up the current client if it exists."""
        if self._client is not None:
            try:
                # Try to stop the client if it has a stop method
                if hasattr(self._client, "__exit__"):
                    self._client.__exit__(None, None, None)
            except (OSError, RuntimeError):
                logger.debug("Error cleaning up MCP client", exc_info=True)
            self._is_started = False

    def _ensure_client(self) -> Any:
        """Ensure we have a valid client, creating one if needed."""
        if self._client is None:
            self._client = self._create_client()
        return self._client

    # -------------------------------------------------------------------------
    # MCPClient interface methods (delegated to underlying client)
    # -------------------------------------------------------------------------

    def __enter__(self) -> ResilientMCPClient:
        """Enter context manager with retry."""

        def start() -> None:
            client = self._ensure_client()
            client.__enter__()
            self._is_started = True

        self._with_retry(start, "start")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Exit context manager."""
        self._cleanup_client()
        self._client = None

    def list_tools_sync(self) -> list[Any]:
        """List tools with retry logic."""

        def list_tools() -> list[Any]:
            client = self._ensure_client()
            if not self._is_started:
                client.__enter__()
                self._is_started = True
            return client.list_tools_sync()

        return self._with_retry(list_tools, "list_tools")

    # -------------------------------------------------------------------------
    # ToolProvider interface (required by Strands Agent)
    # -------------------------------------------------------------------------

    def add_consumer(self, consumer_id: str) -> None:
        """Register a consumer (ToolProvider interface).

        Delegates to the underlying MCPClient.
        """
        client = self._ensure_client()
        if hasattr(client, "add_consumer"):
            client.add_consumer(consumer_id)

    def remove_consumer(self, consumer_id: str) -> None:
        """Unregister a consumer (ToolProvider interface).

        Delegates to the underlying MCPClient.
        """
        if self._client is not None and hasattr(self._client, "remove_consumer"):
            try:
                self._client.remove_consumer(consumer_id)
            except (OSError, RuntimeError):
                logger.debug("Error removing consumer from MCP client", exc_info=True)

    async def load_tools(self) -> Sequence[AgentTool]:
        """Load tools asynchronously (ToolProvider interface).

        This is the main method Strands calls to discover tools.
        Implements retry logic for resilient tool discovery.
        """

        async def do_load() -> Sequence[AgentTool]:
            client = self._ensure_client()
            if hasattr(client, "load_tools"):
                # MCPClient.load_tools is async
                return await client.load_tools()
            # Fallback to list_tools_sync
            if not self._is_started:
                client.__enter__()
                self._is_started = True
            return client.list_tools_sync()

        # Retry loop for async operation
        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                return await do_load()
            except Exception as e:
                last_error = e
                error_msg = str(e).lower()
                is_retryable = any(
                    phrase in error_msg
                    for phrase in [
                        "failed to start",
                        "initialization failed",
                        "connection refused",
                        "connection reset",
                        "timeout",
                        "temporarily unavailable",
                        "server disconnected",
                        "broken pipe",
                        "network",
                    ]
                )
                if not is_retryable or attempt >= self._max_retries:
                    logger.exception(
                        "MCP %s load_tools failed after %d attempts",
                        self._provider_name,
                        attempt + 1,
                    )
                    raise

                delay = self._calculate_delay(attempt)
                logger.warning(
                    "MCP %s load_tools failed (attempt %d/%d), retrying in %.1fs: %s",
                    self._provider_name,
                    attempt + 1,
                    self._max_retries + 1,
                    delay,
                    e,
                )
                await asyncio.sleep(delay)
                self._cleanup_client()
                self._client = None

        if last_error:
            raise last_error
        msg = f"MCP {self._provider_name} load_tools failed unexpectedly"
        raise RuntimeError(msg)

    def start(self) -> None:
        """Start the MCP client (ToolProvider interface)."""

        def do_start() -> None:
            client = self._ensure_client()
            if hasattr(client, "start"):
                client.start()
            else:
                client.__enter__()
            self._is_started = True

        self._with_retry(do_start, "start")

    def stop(self) -> None:
        """Stop the MCP client (ToolProvider interface)."""
        self._cleanup_client()
        self._client = None

    # -------------------------------------------------------------------------
    # Pass-through for tool calls (these go through the underlying client)
    # -------------------------------------------------------------------------

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attributes to the underlying client.

        This allows the resilient wrapper to be used as a drop-in replacement
        for MCPClient, with any method calls going through to the real client.
        """
        client = self._ensure_client()
        attr = getattr(client, name)

        # If it's a callable, wrap it with retry logic
        if callable(attr):

            def wrapper(*args: Any, **kwargs: Any) -> Any:
                def call() -> Any:
                    # Re-get the attribute in case client was recreated
                    c = self._ensure_client()
                    return getattr(c, name)(*args, **kwargs)

                return self._with_retry(call, name)

            return wrapper

        return attr

    def __repr__(self) -> str:
        return (
            f"ResilientMCPClient(provider={self._provider_name!r}, max_retries={self._max_retries})"
        )
