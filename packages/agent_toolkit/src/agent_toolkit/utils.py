"""Shared utilities for agent toolkit.

Consolidates common utilities to follow DRY principle.
Reference: Clean Code - Chapter 3 (Functions should do one thing)
"""

from __future__ import annotations

from datetime import UTC, datetime


def utc_timestamp() -> str:
    """Return current UTC timestamp in ISO format.

    Returns:
        ISO-formatted timestamp string.
    """
    return datetime.now(UTC).isoformat()
