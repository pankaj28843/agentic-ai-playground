"""Thread-related API models."""

from __future__ import annotations

from pydantic import Field

from assistant_web_backend.models.base import ApiModel
from assistant_web_backend.models.messages import (
    MessagePayload,  # noqa: TC001 (Pydantic needs runtime access)
)


class ThreadSummary(ApiModel):
    """Thread summary payload for list responses."""

    remote_id: str = Field(alias="remoteId")
    title: str | None = None
    status: str


class ThreadListResponse(ApiModel):
    """Thread list response payload."""

    threads: list[ThreadSummary]


class ThreadCreateResponse(ApiModel):
    """Thread creation response payload."""

    remote_id: str = Field(alias="remoteId")


class ThreadRenameRequest(ApiModel):
    """Request payload for renaming a thread."""

    title: str = Field(min_length=1, max_length=200)


class ThreadDetailResponse(ApiModel):
    """Single thread detail response payload."""

    remote_id: str = Field(alias="remoteId")
    title: str | None = None
    status: str
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    model_override: str | None = Field(default=None, alias="modelOverride")
    tool_groups_override: list[str] | None = Field(default=None, alias="toolGroupsOverride")


class ChatRunRequest(ApiModel):
    """Request payload for chat execution."""

    messages: list[MessagePayload]
    thread_id: str | None = Field(default=None, alias="threadId")
    profile: str | None = None
    run_mode: str | None = Field(default=None, alias="runMode")
    model_override: str | None = Field(default=None, alias="modelOverride")
    tool_groups_override: list[str] | None = Field(default=None, alias="toolGroupsOverride")
