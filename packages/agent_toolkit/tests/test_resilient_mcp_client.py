"""Tests for ResilientMCPClient retry and reconnection logic."""

from unittest.mock import MagicMock

import pytest
from agent_toolkit.mcp.resilient_client import ResilientMCPClient


class TestResilientMCPClient:
    """Tests for ResilientMCPClient."""

    def test_successful_operation_no_retry(self):
        """Operations that succeed should not trigger retries."""
        mock_client = MagicMock()
        mock_client.list_tools_sync.return_value = ["tool1", "tool2"]

        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return mock_client

        resilient = ResilientMCPClient(factory, max_retries=3)
        result = resilient.list_tools_sync()

        assert result == ["tool1", "tool2"]
        assert call_count == 1

    def test_retry_on_connection_error(self):
        """Should retry on connection errors."""
        mock_client = MagicMock()
        call_count = 0

        def list_tools():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError("connection refused")
            return ["tool1"]

        mock_client.list_tools_sync = list_tools

        resilient = ResilientMCPClient(
            lambda: mock_client,
            max_retries=3,
            initial_delay=0.01,  # Fast for testing
        )
        result = resilient.list_tools_sync()

        assert result == ["tool1"]
        assert call_count == 3

    def test_max_retries_exceeded(self):
        """Should raise after max retries exceeded."""
        mock_client = MagicMock()
        mock_client.list_tools_sync.side_effect = RuntimeError("connection refused")

        resilient = ResilientMCPClient(
            lambda: mock_client,
            max_retries=2,
            initial_delay=0.01,
        )

        with pytest.raises(RuntimeError, match="connection refused"):
            resilient.list_tools_sync()

        # Should have tried 3 times (initial + 2 retries)
        assert mock_client.list_tools_sync.call_count == 3

    def test_non_retryable_error(self):
        """Non-retryable errors should fail immediately."""
        mock_client = MagicMock()
        mock_client.list_tools_sync.side_effect = ValueError("invalid argument")

        resilient = ResilientMCPClient(
            lambda: mock_client,
            max_retries=3,
            initial_delay=0.01,
        )

        with pytest.raises(ValueError, match="invalid argument"):
            resilient.list_tools_sync()

        # Should only try once for non-retryable errors
        assert mock_client.list_tools_sync.call_count == 1

    def test_exponential_backoff_calculation(self):
        """Verify exponential backoff delay calculation."""
        resilient = ResilientMCPClient(
            MagicMock,
            initial_delay=1.0,
            max_delay=30.0,
            backoff_multiplier=2.0,
        )

        assert resilient._calculate_delay(0) == 1.0  # noqa: SLF001
        assert resilient._calculate_delay(1) == 2.0  # noqa: SLF001
        assert resilient._calculate_delay(2) == 4.0  # noqa: SLF001
        assert resilient._calculate_delay(3) == 8.0  # noqa: SLF001
        # Should cap at max_delay
        assert resilient._calculate_delay(10) == 30.0  # noqa: SLF001

    def test_repr(self):
        """Test string representation."""
        resilient = ResilientMCPClient(
            MagicMock,
            provider_name="techdocs",
            max_retries=5,
        )
        assert "techdocs" in repr(resilient)
        assert "5" in repr(resilient)

    def test_context_manager(self):
        """Test context manager protocol."""
        mock_client = MagicMock()
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=None)

        resilient = ResilientMCPClient(lambda: mock_client)

        with resilient as ctx:
            assert ctx is resilient
            mock_client.__enter__.assert_called_once()

        mock_client.__exit__.assert_called_once()
