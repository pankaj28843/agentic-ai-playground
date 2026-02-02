from __future__ import annotations

import tomllib
from dataclasses import dataclass

from agent_toolkit.config.config_paths import resolve_config_path


@dataclass(frozen=True)
class SwarmPreset:
    """Configuration for swarm presets."""

    name: str
    max_handoffs: int
    max_iterations: int
    execution_timeout: float
    node_timeout: float


def load_swarm_presets() -> dict[str, SwarmPreset]:
    """Load swarm presets from TOML (bundled or external)."""
    path = resolve_config_path("swarm_presets")
    if not path.exists():
        return {}

    with path.open("rb") as file:
        data = tomllib.load(file)

    presets = {}
    for name, preset in data.get("presets", {}).items():
        presets[name] = SwarmPreset(
            name=preset.get("name", name),
            max_handoffs=int(preset.get("max_handoffs", 12)),
            max_iterations=int(preset.get("max_iterations", 12)),
            execution_timeout=float(preset.get("execution_timeout", 300.0)),
            node_timeout=float(preset.get("node_timeout", 90.0)),
        )
    return presets
