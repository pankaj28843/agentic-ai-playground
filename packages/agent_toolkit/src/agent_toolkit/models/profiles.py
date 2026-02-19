"""Pydantic models for agent profiles."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ProfileType(StrEnum):
    """Profile visibility type."""

    INTERNAL = "internal"
    EXTERNAL = "external"


class AgentProfile(BaseModel, frozen=True):
    """Configuration for a single agent profile."""

    name: str
    description: str = ""
    model: str = ""
    system_prompt: str = ""
    tools: list[str] = Field(default_factory=list)
    tool_groups: list[str] = Field(default_factory=list)
    extends: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
    constraints: dict[str, Any] = Field(default_factory=dict)
    profile_type: ProfileType = ProfileType.INTERNAL
    # Model-specific config overrides (temperature, max_tokens, etc.)
    model_config_overrides: dict[str, Any] = Field(default_factory=dict, alias="model_config")

    model_config = {"populate_by_name": True}
