"""Resource loader models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True)
class ResourceDiagnostics:
    """Diagnostics collected during resource discovery."""

    warnings: list[str] = field(default_factory=list)

    def warn(self, message: str) -> None:
        """Record a warning message."""
        self.warnings.append(message)


@dataclass(frozen=True)
class ContextFile:
    """Context file content loaded from AGENTS.md."""

    path: str
    content: str


@dataclass(frozen=True)
class SkillDefinition:
    """Skill definition loaded from SKILL.md or markdown."""

    name: str
    description: str
    content: str
    file_path: str
    base_dir: str
    source: Literal["global", "project", "explicit"]


@dataclass(frozen=True)
class PromptTemplate:
    """Prompt template definition."""

    name: str
    description: str
    content: str
    source: Literal["global", "project", "explicit"]


@dataclass(frozen=True)
class ResourceBundle:
    """Aggregated resources for agent context."""

    context_files: list[ContextFile]
    skills: list[SkillDefinition]
    prompts: list[PromptTemplate]
    diagnostics: ResourceDiagnostics
