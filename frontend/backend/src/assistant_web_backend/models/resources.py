"""Resource payloads for skills and prompts."""

from __future__ import annotations

from pydantic import Field

from assistant_web_backend.models.base import ApiModel


class ResourceDiagnostics(ApiModel):
    """Diagnostics for resource discovery."""

    warnings: list[str] = Field(default_factory=list)


class SkillResource(ApiModel):
    """Skill metadata and content payload."""

    name: str
    description: str
    content: str
    source: str


class PromptResource(ApiModel):
    """Prompt metadata and content payload."""

    name: str
    description: str
    content: str
    source: str


class ResourcesResponse(ApiModel):
    """Combined resource payloads for skills and prompts."""

    skills: list[SkillResource]
    prompts: list[PromptResource]
    diagnostics: ResourceDiagnostics
