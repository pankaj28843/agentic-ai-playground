"""Service for loading skill and prompt resources."""

from __future__ import annotations

from pathlib import Path

from agent_toolkit.resources import ResourceLoader

from assistant_web_backend.services.settings import get_settings


def load_resources() -> object:
    """Load skills and prompts using the project resource loader."""
    settings = get_settings()
    cwd = Path.cwd()
    loader = ResourceLoader(cwd=cwd, agent_dir=settings.playground_config_dir)
    return loader.load()
