from __future__ import annotations

from pathlib import Path

from agent_toolkit.subagents.loader import SubagentLoader


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_subagent_loader_prefers_project_definitions(tmp_path: Path) -> None:
    global_dir = tmp_path / "config"
    project_dir = tmp_path / "project"

    _write(
        global_dir / "agents" / "scout.md",
        """---\nname: scout\ndescription: \"Global scout\"\nmodel: \"bedrock.nova-micro\"\ntools: []\n---\nGlobal prompt\n""",
    )
    _write(
        project_dir / ".pi" / "agents" / "scout.md",
        """---\nname: scout\ndescription: \"Project scout\"\nmodel: \"bedrock.nova-micro\"\ntools: []\n---\nProject prompt\n""",
    )

    loader = SubagentLoader(cwd=project_dir, agent_dir=global_dir)
    catalog = loader.load()

    definition = catalog.definitions.get("scout")
    assert definition is not None
    assert definition.description == "Project scout"
    assert definition.source == "project"
