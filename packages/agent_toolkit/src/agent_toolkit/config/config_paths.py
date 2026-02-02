"""Unified configuration path resolution.

All TOML configuration files can be loaded from:
1. Bundled defaults (package resources)
2. External directory (PLAYGROUND_CONFIG_DIR environment variable, mandatory)

External files override bundled defaults for non-profile configs.
Profile configs (agents.toml, tool_groups.toml) use merge semantics.
"""

from __future__ import annotations

import os
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_toolkit.config.settings import Settings

# Default external config directory (fallback for local dev without .env)
DEFAULT_CONFIG_DIR = "./config"

# Config file names
CONFIG_FILES = {
    "agents": "agents.toml",
    "tool_groups": "tool_groups.toml",
    "graphs": "graphs.toml",
    "swarms": "swarms.toml",
    "public_profiles": "public_profiles.toml",
    "swarm_presets": "swarm_presets.toml",
    "mcp_providers": "mcp_providers.toml",
    "providers": "providers.toml",
}

# Module-level override (can be set via set_config_dir)
_config_dir_override: str | None = None


def set_config_dir(path: str | None) -> None:
    """Set a module-level config directory override.

    Useful when Settings object provides the config dir.

    Args:
        path: The config directory path, or None to clear override.
    """
    global _config_dir_override  # noqa: PLW0603
    _config_dir_override = path


def get_config_dir(settings: Settings | None = None) -> Path:
    """Get the external config directory.

    Priority:
    1. Module-level override (set via set_config_dir)
    2. Settings object (if provided)
    3. PLAYGROUND_CONFIG_DIR environment variable (mandatory in production)
    4. Default: ./config (local development fallback)

    Args:
        settings: Optional Settings object to read config dir from.

    Returns:
        Expanded path to the config directory.
    """
    # Priority 1: Module override
    if _config_dir_override:
        return Path(_config_dir_override).expanduser()

    # Priority 2: Settings object
    if settings and hasattr(settings, "playground_config_dir"):
        return Path(settings.playground_config_dir).expanduser()

    # Priority 3: Environment variable, Priority 4: Default
    config_dir = os.getenv("PLAYGROUND_CONFIG_DIR", DEFAULT_CONFIG_DIR)
    return Path(config_dir).expanduser()


def get_bundled_path(config_name: str) -> Path:
    """Get the bundled (package resource) path for a config file.

    Args:
        config_name: One of 'agents', 'tool_groups', 'graphs', 'swarms',
                     'swarm_presets', 'mcp_providers'

    Returns:
        Path to the bundled config file.

    Raises:
        ValueError: If config_name is not recognized.
    """
    filename = CONFIG_FILES.get(config_name)
    if not filename:
        msg = f"Unknown config: {config_name}. Valid: {list(CONFIG_FILES.keys())}"
        raise ValueError(msg)

    # mcp_providers is in the mcp subpackage
    if config_name == "mcp_providers":
        return Path(resources.files("agent_toolkit.mcp").joinpath(filename))

    return Path(resources.files("agent_toolkit.config").joinpath(filename))


def get_external_path(config_name: str) -> Path:
    """Get the external override path for a config file.

    Args:
        config_name: One of 'agents', 'tool_groups', 'graphs', 'swarms',
                     'swarm_presets', 'mcp_providers'

    Returns:
        Path to the external config file (may not exist).
    """
    filename = CONFIG_FILES.get(config_name)
    if not filename:
        msg = f"Unknown config: {config_name}. Valid: {list(CONFIG_FILES.keys())}"
        raise ValueError(msg)

    return get_config_dir() / filename


def get_config_paths(config_name: str) -> tuple[Path, Path | None]:
    """Get both bundled and external paths for a config file.

    Args:
        config_name: The config file identifier.

    Returns:
        Tuple of (bundled_path, external_path or None if doesn't exist).
    """
    bundled = get_bundled_path(config_name)
    external = get_external_path(config_name)

    return bundled, external if external.exists() else None


def resolve_config_path(config_name: str, prefer_external: bool = True) -> Path:
    """Resolve to the best available config path.

    For non-profile configs, external completely overrides bundled.
    For profile configs, use get_all_config_paths() for merge loading.

    Args:
        config_name: The config file identifier.
        prefer_external: If True, use external when it exists.

    Returns:
        Path to the config file to use.
    """
    bundled, external = get_config_paths(config_name)

    if prefer_external and external:
        return external

    return bundled


def get_all_config_paths(config_name: str) -> list[Path]:
    """Get all paths for configs that support merging (profiles, tool_groups).

    When external config exists, ONLY external is returned (bundled is ignored).
    This allows external config to fully replace bundled defaults.

    Args:
        config_name: The config file identifier.

    Returns:
        List of paths that exist, in loading order.
    """
    bundled, external = get_config_paths(config_name)

    # If external config exists, use ONLY external (ignore bundled)
    if external and external.exists():
        return [external]

    # Fall back to bundled if no external config
    return [bundled] if bundled.exists() else []


def ensure_config_dir() -> Path:
    """Ensure the external config directory exists.

    Returns:
        Path to the config directory.
    """
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir
