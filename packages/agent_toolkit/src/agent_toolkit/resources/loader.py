"""Resource loader for context files, skills, and prompt templates."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable

from agent_toolkit.markdown_utils import first_non_empty_line, parse_frontmatter
from agent_toolkit.resources.models import (
    ContextFile,
    PromptTemplate,
    ResourceBundle,
    ResourceDiagnostics,
    SkillDefinition,
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _is_valid_skill_name(name: str) -> bool:
    if not name:
        return False
    if name.startswith("-") or name.endswith("-"):
        return False
    if "--" in name:
        return False
    return all(ch.islower() or ch.isdigit() or ch == "-" for ch in name)


def _discover_agents_files(
    cwd: Path, agent_dir: Path, diagnostics: ResourceDiagnostics
) -> list[ContextFile]:
    context_files: list[ContextFile] = []

    # Global AGENTS.md
    global_agents = agent_dir / "AGENTS.md"
    if global_agents.exists():
        context_files.append(
            ContextFile(path=str(global_agents), content=_read_text(global_agents))
        )

    # Walk up from cwd to root
    for current in [cwd, *cwd.parents]:
        agents_path = current / "AGENTS.md"
        if agents_path.exists():
            context_files.append(
                ContextFile(path=str(agents_path), content=_read_text(agents_path))
            )

    if not context_files:
        diagnostics.warn("No AGENTS.md context files discovered.")
    return context_files


def _discover_skill_files(base: Path) -> list[Path]:
    if not base.exists():
        return []

    skill_files = list(base.glob("*.md"))
    skill_files += list(base.rglob("SKILL.md"))
    return skill_files


def _load_skills(
    paths: Iterable[Path], source: str, diagnostics: ResourceDiagnostics
) -> list[SkillDefinition]:
    skills: list[SkillDefinition] = []
    seen: set[str] = set()

    for skill_path in paths:
        try:
            text = _read_text(skill_path)
        except FileNotFoundError:
            diagnostics.warn(f"Skill file not found: {skill_path}")
            continue

        meta, body = parse_frontmatter(text)
        base_dir = str(skill_path.parent)
        name = meta.get("name") or skill_path.parent.name
        description = meta.get("description", "")

        if not description:
            diagnostics.warn(f"Skill missing description: {skill_path}")
            continue
        if not _is_valid_skill_name(name):
            diagnostics.warn(f"Invalid skill name '{name}' in {skill_path}")
            continue
        if name in seen:
            diagnostics.warn(f"Duplicate skill '{name}' ignored from {skill_path}")
            continue

        seen.add(name)
        skills.append(
            SkillDefinition(
                name=name,
                description=description,
                content=body.strip() or text.strip(),
                file_path=str(skill_path),
                base_dir=base_dir,
                source=source,  # type: ignore[arg-type]
            )
        )
    return skills


def _load_prompts(
    prompt_dir: Path, source: str, diagnostics: ResourceDiagnostics
) -> list[PromptTemplate]:
    prompts: list[PromptTemplate] = []
    if not prompt_dir.exists():
        return prompts
    for path in prompt_dir.glob("*.md"):
        text = _read_text(path)
        meta, body = parse_frontmatter(text)
        name = path.stem
        description = meta.get("description") or first_non_empty_line(body)
        if not description:
            diagnostics.warn(f"Prompt template missing description: {path}")
            description = name
        prompts.append(
            PromptTemplate(
                name=name,
                description=description,
                content=body.strip() or text.strip(),
                source=source,  # type: ignore[arg-type]
            )
        )
    return prompts


class ResourceLoader:
    """Discover context files, skills, and prompts from global/project scopes."""

    def __init__(
        self,
        cwd: str | Path,
        agent_dir: str | Path,
        extra_skill_paths: Iterable[str | Path] | None = None,
        extra_prompt_paths: Iterable[str | Path] | None = None,
        extra_context_files: Iterable[str | Path] | None = None,
    ) -> None:
        self.cwd = Path(cwd)
        self.agent_dir = Path(agent_dir)
        self.extra_skill_paths = [Path(p) for p in (extra_skill_paths or [])]
        self.extra_prompt_paths = [Path(p) for p in (extra_prompt_paths or [])]
        self.extra_context_files = [Path(p) for p in (extra_context_files or [])]

    def load(self) -> ResourceBundle:
        """Load context files, skills, and prompts."""
        diagnostics = ResourceDiagnostics()

        context_files = _discover_agents_files(self.cwd, self.agent_dir, diagnostics)
        for extra in self.extra_context_files:
            if extra.exists():
                context_files.append(ContextFile(path=str(extra), content=_read_text(extra)))
            else:
                diagnostics.warn(f"Context file not found: {extra}")

        # Skills
        global_skills_dir = self.agent_dir / "skills"
        project_skills_dir = self.cwd / ".pi" / "skills"

        skill_paths = _discover_skill_files(global_skills_dir)
        skills = _load_skills(skill_paths, "global", diagnostics)
        skills += _load_skills(_discover_skill_files(project_skills_dir), "project", diagnostics)

        for extra in self.extra_skill_paths:
            if extra.is_dir():
                skills += _load_skills(_discover_skill_files(extra), "explicit", diagnostics)
            elif extra.is_file():
                skills += _load_skills([extra], "explicit", diagnostics)
            else:
                diagnostics.warn(f"Skill path not found: {extra}")

        # Prompts
        global_prompts_dir = self.agent_dir / "prompts"
        project_prompts_dir = self.cwd / ".pi" / "prompts"

        prompts = _load_prompts(global_prompts_dir, "global", diagnostics)
        prompts += _load_prompts(project_prompts_dir, "project", diagnostics)

        for extra in self.extra_prompt_paths:
            if extra.is_dir():
                prompts += _load_prompts(extra, "explicit", diagnostics)
            elif extra.is_file():
                text = _read_text(extra)
                meta, body = parse_frontmatter(text)
                name = extra.stem
                description = meta.get("description") or first_non_empty_line(body)
                prompts.append(
                    PromptTemplate(
                        name=name,
                        description=description or name,
                        content=body.strip() or text.strip(),
                        source="explicit",
                    )
                )
            else:
                diagnostics.warn(f"Prompt path not found: {extra}")

        return ResourceBundle(
            context_files=context_files,
            skills=skills,
            prompts=prompts,
            diagnostics=diagnostics,
        )
