#!/usr/bin/env python3
"""Bootstrap the playground config directory with default configs.

Creates the default config directory and copies all bundled TOML config
files for customization.

Usage:
    uv run python scripts/bootstrap_config.py
    # or
    uv run python scripts/bootstrap_config.py --dir <config-dir>
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from agent_toolkit.config.config_paths import (
    CONFIG_FILES,
    ensure_config_dir,
    get_bundled_path,
)


def bootstrap_config(target_dir: Path | None = None) -> None:
    """Copy bundled configs to the external config directory.

    Args:
        target_dir: Override the default config directory.
    """
    if target_dir:
        config_dir = target_dir
        config_dir.mkdir(parents=True, exist_ok=True)
    else:
        config_dir = ensure_config_dir()

    print(f"Bootstrapping config directory: {config_dir}")
    print()

    for config_name, filename in CONFIG_FILES.items():
        bundled_path = get_bundled_path(config_name)
        target_path = config_dir / filename

        if target_path.exists():
            print(f"  SKIP {filename} (already exists)")
            continue

        if not bundled_path.exists():
            print(f"  WARN {filename} (bundled not found)")
            continue

        shutil.copy(bundled_path, target_path)
        print(f"  COPY {filename}")

    print()
    print("Done! You can now customize the config files.")
    print()
    print("Config files:")
    print("  agents.toml        - Agent profiles with system prompts")
    print("  tool_groups.toml   - Tool groupings for profiles")
    print("  graphs.toml        - Multi-agent graph topologies")
    print("  swarms.toml        - Swarm orchestration configs")
    print("  swarm_presets.toml - Swarm execution presets")
    print("  mcp_providers.toml - MCP server connections")
    print()
    print(f"Set PLAYGROUND_CONFIG_DIR={config_dir} to use a different location.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bootstrap playground config directory with default configs"
    )
    parser.add_argument(
        "--dir",
        type=Path,
        help="Override target directory (default: project config directory)",
    )

    args = parser.parse_args()

    try:
        bootstrap_config(args.dir)
        return 0
    except OSError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
