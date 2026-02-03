from __future__ import annotations

from agent_toolkit.resources.models import (
    ContextFile,
    PromptTemplate,
    ResourceBundle,
    ResourceDiagnostics,
    SkillDefinition,
)


def test_resources_endpoint_returns_resources(client, monkeypatch) -> None:
    bundle = ResourceBundle(
        context_files=[ContextFile(path="/tmp/AGENTS.md", content="")],
        skills=[
            SkillDefinition(
                name="review",
                description="Review instructions",
                content="Review content",
                file_path="/tmp/skills/review/SKILL.md",
                base_dir="/tmp/skills/review",
                source="global",
            )
        ],
        prompts=[
            PromptTemplate(
                name="summarize",
                description="Summarize text",
                content="Summarize content",
                source="global",
            )
        ],
        diagnostics=ResourceDiagnostics(warnings=["warn"]),
    )

    monkeypatch.setattr("assistant_web_backend.routes.config.load_resources", lambda: bundle)

    response = client.get("/api/resources")
    assert response.status_code == 200
    data = response.json()
    assert data["skills"][0]["name"] == "review"
    assert data["prompts"][0]["name"] == "summarize"
    assert data["diagnostics"]["warnings"] == ["warn"]
