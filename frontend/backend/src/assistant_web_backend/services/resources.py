"""Service for loading skill and prompt resources."""

from __future__ import annotations

from pathlib import Path

from agent_toolkit.config import load_settings
from agent_toolkit.resources import ResourceLoader


def load_resources() -> object:
    """Load skills and prompts using the project resource loader."""
    settings = load_settings()
    cwd = Path.cwd()
    loader = ResourceLoader(cwd=cwd, agent_dir=settings.playground_config_dir)
    return loader.load()
