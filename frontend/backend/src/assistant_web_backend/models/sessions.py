"""Session tree API models."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from assistant_web_backend.models.base import ApiModel


class SessionHeaderView(ApiModel):
    """Header for a session tree."""

    id: str
    timestamp: str
    cwd: str | None = None
    parent_session: str | None = Field(default=None, alias="parentSession")


class SessionEntryView(ApiModel):
    """Session entry payload for UI tree rendering."""

    id: str
    parent_id: str | None = Field(alias="parentId")
    type: str
    timestamp: str
    label: str | None = None
    message_role: str | None = Field(default=None, alias="messageRole")
    message_preview: str | None = Field(default=None, alias="messagePreview")
    summary: str | None = None
    custom_type: str | None = Field(default=None, alias="customType")
    from_id: str | None = Field(default=None, alias="fromId")
    details: dict[str, Any] | None = None


class SessionTreeResponse(ApiModel):
    """Response payload for session tree."""

    session_id: str = Field(alias="sessionId")
    header: SessionHeaderView
    entries: list[SessionEntryView]
    roots: list[str]
    children: dict[str, list[str]]
    leaf_id: str | None = Field(default=None, alias="leafId")


class SessionLabelRequest(ApiModel):
    """Request payload to add/update a label."""

    entry_id: str = Field(alias="entryId")
    label: str | None = None


class SessionLabelResponse(ApiModel):
    """Response payload for label updates."""

    status: str
    label_entry_id: str = Field(alias="labelEntryId")
