from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _set_required_env(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    monkeypatch.setenv("PLAYGROUND_CONFIG_DIR", str(repo_root / "config"))
    monkeypatch.setenv("TECHDOCS_MCP_URL", "https://techdocs.example.com/mcp")
    monkeypatch.setenv("PHOENIX_ENABLED", "false")
    monkeypatch.setenv("PHOENIX_COLLECTOR_ENDPOINT", "")
