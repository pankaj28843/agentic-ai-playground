"""Settings provider for backend services.

Provides a cached settings instance to avoid repeated environment parsing and
config file reads on each request.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from agent_toolkit.config import load_settings

if TYPE_CHECKING:
    from agent_toolkit.models.settings import Settings


@lru_cache
def get_settings() -> Settings:
    """Return cached runtime settings."""
    return load_settings()
