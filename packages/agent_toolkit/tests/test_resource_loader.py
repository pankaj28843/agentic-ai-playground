from __future__ import annotations

from pathlib import Path

from agent_toolkit.resources import ResourceLoader


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_resource_loader_discovers_context_and_prompts(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    project_dir = tmp_path / "project"
    _write(agent_dir / "AGENTS.md", "# Global rules")
    _write(project_dir / "AGENTS.md", "# Project rules")
    _write(project_dir / ".pi" / "prompts" / "review.md", "---\ndescription: Review\n---\nCheck")

    loader = ResourceLoader(cwd=project_dir, agent_dir=agent_dir)
    bundle = loader.load()

    assert len(bundle.context_files) == 2
    assert any("Global rules" in item.content for item in bundle.context_files)
    assert any("Project rules" in item.content for item in bundle.context_files)
    assert bundle.prompts[0].name == "review"
    assert bundle.prompts[0].description == "Review"
    assert bundle.prompts[0].content


def test_resource_loader_discovers_skills_and_warnings(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    project_dir = tmp_path / "project"

    valid_skill = "---\nname: my-skill\ndescription: Do work\n---\n# Skill"
    invalid_skill = "---\nname: BadSkill\ndescription: Nope\n---\n# Skill"

    _write(agent_dir / "skills" / "my-skill" / "SKILL.md", valid_skill)
    _write(project_dir / ".pi" / "skills" / "bad" / "SKILL.md", invalid_skill)

    loader = ResourceLoader(cwd=project_dir, agent_dir=agent_dir)
    bundle = loader.load()

    assert len(bundle.skills) == 1
    assert bundle.skills[0].name == "my-skill"
    assert bundle.skills[0].content
    assert bundle.diagnostics.warnings


def test_resource_loader_uses_explicit_paths(tmp_path: Path) -> None:
    agent_dir = tmp_path / "agent"
    project_dir = tmp_path / "project"

    extra_skill_path = tmp_path / "extra" / "skill" / "SKILL.md"
    _write(extra_skill_path, "---\nname: extra-skill\ndescription: Extra\n---\n# Skill")

    loader = ResourceLoader(
        cwd=project_dir,
        agent_dir=agent_dir,
        extra_skill_paths=[extra_skill_path],
        extra_prompt_paths=[tmp_path / "extra" / "prompt.md"],
    )
    _write(tmp_path / "extra" / "prompt.md", "Prompt body")

    bundle = loader.load()
    assert any(skill.name == "extra-skill" for skill in bundle.skills)
    assert any(prompt.name == "prompt" for prompt in bundle.prompts)
