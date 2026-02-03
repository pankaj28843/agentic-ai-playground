"""Configuration-related API models."""

from __future__ import annotations

from pydantic import Field

from assistant_web_backend.models.base import ApiModel


class PhoenixConfigResponse(ApiModel):
    """Phoenix observability configuration."""

    enabled: bool
    base_url: str | None = Field(default=None, alias="baseUrl")
    project_name: str | None = Field(default=None, alias="projectName")
    project_id: str | None = Field(default=None, alias="projectId")


class ToolGroupSummary(ApiModel):
    """Tool group summary for settings UI."""

    name: str
    description: str
    tools: list[str]
    capabilities: list[str] = Field(default_factory=list)


class ProfileDefaults(ApiModel):
    """Defaults for a public profile."""

    profile_id: str = Field(alias="profileId")
    model: str | None = None
    tool_groups: list[str] = Field(default_factory=list, alias="toolGroups")


class SettingsResponse(ApiModel):
    """Runtime settings response."""

    models: list[str]
    default_model: str | None = Field(default=None, alias="defaultModel")
    tool_groups: list[ToolGroupSummary] = Field(default_factory=list, alias="toolGroups")
    profile_defaults: list[ProfileDefaults] = Field(default_factory=list, alias="profileDefaults")
    warnings: list[str] = Field(default_factory=list)
