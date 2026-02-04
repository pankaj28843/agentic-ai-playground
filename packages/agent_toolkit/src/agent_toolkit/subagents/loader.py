"""Load subagent definitions from markdown files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

from agent_toolkit.markdown_utils import first_non_empty_line, parse_frontmatter
from agent_toolkit.subagents.models import SubagentDefinition


@dataclass
class SubagentDiagnostics:
    """Diagnostics captured during subagent discovery."""

    warnings: list[str] = field(default_factory=list)

    def warn(self, message: str) -> None:
        """Record a discovery warning."""
        self.warnings.append(message)


@dataclass(frozen=True)
class SubagentCatalog:
    """Catalog of discovered subagent definitions."""

    definitions: dict[str, SubagentDefinition]
    diagnostics: SubagentDiagnostics


def _parse_list(value: str | None) -> list[str]:
    if not value:
        return []
    raw = value.strip()
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return [item.strip() for item in raw.split(",") if item.strip()]


def _discover_agent_files(base: Path) -> list[Path]:
    if not base.exists():
        return []
    return sorted(base.glob("*.md"))


def _load_definitions(
    paths: Iterable[Path], source: str, diagnostics: SubagentDiagnostics
) -> dict[str, SubagentDefinition]:
    definitions: dict[str, SubagentDefinition] = {}
    for path in paths:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError:
            diagnostics.warn(f"Subagent file not found: {path}")
            continue
        meta, body = parse_frontmatter(text)
        name = meta.get("name") or path.stem
        description = meta.get("description") or first_non_empty_line(body)
        model = meta.get("model", "")
        tools = _parse_list(meta.get("tools"))
        tool_groups = _parse_list(meta.get("tool_groups"))
        system_prompt = body.strip()

        if not description:
            diagnostics.warn(f"Subagent missing description: {path}")
            continue
        if not system_prompt:
            diagnostics.warn(f"Subagent missing system prompt: {path}")
            continue
        if name in definitions:
            diagnostics.warn(f"Duplicate subagent '{name}' ignored from {path}")
            continue

        definitions[name] = SubagentDefinition(
            name=name,
            description=description,
            system_prompt=system_prompt,
            model=model,
            tools=tools,
            tool_groups=tool_groups,
            source=source,
        )
    return definitions


class SubagentLoader:
    """Discover subagent definitions from global/project markdown files."""

    def __init__(self, cwd: str | Path, agent_dir: str | Path) -> None:
        self.cwd = Path(cwd)
        self.agent_dir = Path(agent_dir)

    def load(self) -> SubagentCatalog:
        """Load subagent definitions from configured directories."""
        diagnostics = SubagentDiagnostics()

        global_dir = self.agent_dir / "agents"
        project_dir = self.cwd / ".pi" / "agents"

        global_defs = _load_definitions(_discover_agent_files(global_dir), "global", diagnostics)
        project_defs = _load_definitions(_discover_agent_files(project_dir), "project", diagnostics)

        definitions = {**global_defs, **project_defs}

        if not definitions:
            diagnostics.warn("No subagent definitions discovered.")

        return SubagentCatalog(definitions=definitions, diagnostics=diagnostics)
