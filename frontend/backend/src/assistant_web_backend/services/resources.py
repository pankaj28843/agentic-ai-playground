"""Service for loading skill and prompt resources."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from agent_toolkit.resources import ResourceLoader

from assistant_web_backend.services.settings import get_settings


@lru_cache
def load_resources() -> object:
    """Load skills and prompts using the project resource loader."""
    settings = get_settings()
    cwd = Path.cwd()
    loader = ResourceLoader(cwd=cwd, agent_dir=settings.playground_config_dir)
    return loader.load()


def clear_resources_cache() -> None:
    """Clear cached resources (for tests or forced refresh)."""
    load_resources.cache_clear()
