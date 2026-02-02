"""Profile-related API models."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from assistant_web_backend.models.base import ApiModel


class ProfileSummary(ApiModel):
    """Agent profile summary payload."""

    id: str
    name: str
    description: str | None = None
    entrypoint_type: str | None = Field(default=None, alias="entrypointType")
    entrypoint_reference: str | None = Field(default=None, alias="entrypointReference")
    default: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ProfilesResponse(ApiModel):
    """Response payload for available profiles and run modes."""

    profiles: list[ProfileSummary]
    run_modes: list[str] = Field(alias="runModes")
    default_run_mode: str | None = Field(default=None, alias="defaultRunMode")
