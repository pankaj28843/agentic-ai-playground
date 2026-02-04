"""Message-related API models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from assistant_web_backend.models.base import ApiModel


class MessagePayload(ApiModel):
    """Message payload stored in thread history."""

    id: str
    role: Literal["user", "assistant", "system", "tool"]
    content: list[dict[str, Any]]
    created_at: str = Field(alias="createdAt")
    phoenix_trace_id: str | None = Field(default=None, alias="phoenixTraceId")
    # Full Phoenix URLs (built by backend, ready for display)
    phoenix_trace_url: str | None = Field(default=None, alias="phoenixTraceUrl")
    phoenix_session_url: str | None = Field(default=None, alias="phoenixSessionUrl")
    # New fields for run metadata
    run_profile: str | None = Field(default=None, alias="runProfile")
    run_mode: str | None = Field(default=None, alias="runMode")
    execution_mode: str | None = Field(default=None, alias="executionMode")
    entrypoint_reference: str | None = Field(default=None, alias="entrypointReference")
    model_id: str | None = Field(default=None, alias="modelId")
    phoenix_session_id: str | None = Field(default=None, alias="phoenixSessionId")
    session_entry_id: str | None = Field(default=None, alias="sessionEntryId")


class MessageAppendRequest(ApiModel):
    """Request payload for appending a message."""

    message: MessagePayload
    phoenix_trace_id: str | None = Field(default=None, alias="phoenixTraceId")
    # New fields for run metadata
    run_profile: str | None = Field(default=None, alias="runProfile")
    run_mode: str | None = Field(default=None, alias="runMode")
    execution_mode: str | None = Field(default=None, alias="executionMode")
    entrypoint_reference: str | None = Field(default=None, alias="entrypointReference")
    model_id: str | None = Field(default=None, alias="modelId")
    phoenix_session_id: str | None = Field(default=None, alias="phoenixSessionId")
    parent_session_entry_id: str | None = Field(default=None, alias="parentSessionEntryId")


class ThreadMessagesResponse(ApiModel):
    """Response payload for thread messages."""

    messages: list[MessagePayload]


class TitleRequest(ApiModel):
    """Request payload for title generation."""

    messages: list[MessagePayload]


class TitleResponse(ApiModel):
    """Response payload for title generation."""

    title: str


class ToolCallStatus(ApiModel):
    """Status of a tool call."""

    type: Literal["running", "complete", "incomplete"] = "running"
    reason: str | None = None


class ContentPart(ApiModel):
    """A content part in an assistant message.

    Matches assistant-ui content part format for tool-call, text, reasoning, and agent-event.
    """

    type: Literal["text", "tool-call", "reasoning", "agent-event"]
    # For text and reasoning:
    text: str | None = None
    # For tool-call:
    tool_name: str | None = Field(default=None, alias="toolName")
    tool_call_id: str | None = Field(default=None, alias="toolCallId")
    args: dict[str, Any] | None = None
    args_text: str | None = Field(default=None, alias="argsText")
    result: Any | None = None
    result_full: Any | None = Field(default=None, alias="resultFull")
    result_truncated: bool | None = Field(default=None, alias="resultTruncated")
    is_error: bool | None = Field(default=None, alias="isError")
    status: ToolCallStatus | None = None
    # Timestamp for chronological ordering in trace panel
    timestamp: str | None = None
    # For agent-event (multi-agent orchestration tracing):
    agent_name: str | None = Field(default=None, alias="agentName")
    event_type: str | None = Field(default=None, alias="eventType")  # start, complete, handoff
    from_agents: list[str] | None = Field(default=None, alias="fromAgents")
    to_agents: list[str] | None = Field(default=None, alias="toAgents")
    handoff_message: str | None = Field(default=None, alias="handoffMessage")  # Reason for handoff
    # For tool-call: which agent made this call (in multi-agent modes)
    calling_agent: str | None = Field(default=None, alias="callingAgent")


class RichStreamChunk(ApiModel):
    """Rich streaming response chunk with content array."""

    content: list[ContentPart]
    # Phoenix telemetry metadata (included on final chunk)
    phoenix_trace_id: str | None = Field(default=None, alias="phoenixTraceId")
    phoenix_session_id: str | None = Field(default=None, alias="phoenixSessionId")
    # Runtime metadata (included on final chunk for debugging)
    run_mode: str | None = Field(default=None, alias="runMode")
    profile_name: str | None = Field(default=None, alias="profileName")
    model_id: str | None = Field(default=None, alias="modelId")
    # New fields for resolved execution metadata
    execution_mode: str | None = Field(default=None, alias="executionMode")
    entrypoint_reference: str | None = Field(default=None, alias="entrypointReference")
