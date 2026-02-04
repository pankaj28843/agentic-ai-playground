"""Plan mode configuration utilities."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

DEFAULT_SHELL_ALLOWLIST = (
    "ls",
    "pwd",
    "rg",
    "cat",
    "sed",
    "head",
    "tail",
    "wc",
    "which",
    "git status",
    "git diff",
    "python -V",
    "python --version",
    "node -v",
    "npm -v",
    "pnpm -v",
)


def _normalize_allowlist(value: Iterable[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    seen: set[str] = set()
    items: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return tuple(items)


@dataclass(frozen=True)
class PlanModeSettings:
    """Settings for plan mode enforcement."""

    enabled: bool
    shell_allowlist: tuple[str, ...]

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, Any] | None) -> PlanModeSettings:
        """Build plan mode settings from agent metadata."""
        if not metadata:
            return cls(enabled=False, shell_allowlist=())

        raw = metadata.get("plan_mode")
        if not isinstance(raw, Mapping):
            return cls(enabled=False, shell_allowlist=())

        enabled = bool(raw.get("enabled", False))
        allowlist_value = raw.get("allowed_shell")
        if allowlist_value is None and enabled:
            allowlist = DEFAULT_SHELL_ALLOWLIST
        else:
            allowlist = _normalize_allowlist(allowlist_value)

        return cls(enabled=enabled, shell_allowlist=allowlist)
