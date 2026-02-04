"""Pydantic models for the assistant web backend API.

This package contains all request/response models organized by domain.
"""

from assistant_web_backend.models.base import ApiModel
from assistant_web_backend.models.config import (
    PhoenixConfigResponse,
    ProfileDefaults,
    SettingsResponse,
    ToolGroupSummary,
)
from assistant_web_backend.models.messages import (
    ContentPart,
    MessageAppendRequest,
    MessagePayload,
    RichStreamChunk,
    ThreadMessagesResponse,
    TitleRequest,
    TitleResponse,
    ToolCallStatus,
)
from assistant_web_backend.models.profiles import ProfilesResponse, ProfileSummary
from assistant_web_backend.models.resources import (
    PromptResource,
    ResourceDiagnostics,
    ResourcesResponse,
    SkillResource,
)
from assistant_web_backend.models.sessions import (
    SessionEntryView,
    SessionHeaderView,
    SessionLabelRequest,
    SessionLabelResponse,
    SessionTreeResponse,
)
from assistant_web_backend.models.threads import (
    ChatRunRequest,
    ThreadCreateResponse,
    ThreadDetailResponse,
    ThreadListResponse,
    ThreadRenameRequest,
    ThreadSummary,
)

__all__ = [
    "ApiModel",
    "ChatRunRequest",
    "ContentPart",
    "MessageAppendRequest",
    "MessagePayload",
    "PhoenixConfigResponse",
    "ProfileDefaults",
    "ProfileSummary",
    "ProfilesResponse",
    "PromptResource",
    "ResourceDiagnostics",
    "ResourcesResponse",
    "RichStreamChunk",
    "SessionEntryView",
    "SessionHeaderView",
    "SessionLabelRequest",
    "SessionLabelResponse",
    "SessionTreeResponse",
    "SettingsResponse",
    "SkillResource",
    "ThreadCreateResponse",
    "ThreadDetailResponse",
    "ThreadListResponse",
    "ThreadMessagesResponse",
    "ThreadRenameRequest",
    "ThreadSummary",
    "TitleRequest",
    "TitleResponse",
    "ToolCallStatus",
    "ToolGroupSummary",
]
