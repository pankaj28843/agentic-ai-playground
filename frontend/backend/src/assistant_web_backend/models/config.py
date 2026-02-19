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
