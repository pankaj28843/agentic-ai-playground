"""Thread management routes."""

from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from assistant_web_backend.dependencies import get_storage
from assistant_web_backend.models.messages import (
    MessageAppendRequest,
    MessagePayload,
    ThreadMessagesResponse,
    TitleRequest,
    TitleResponse,
)
from assistant_web_backend.models.sessions import (
    SessionLabelRequest,
    SessionLabelResponse,
    SessionTreeResponse,
)
from assistant_web_backend.models.threads import (
    ThreadCreateResponse,
    ThreadDetailResponse,
    ThreadListResponse,
    ThreadRenameRequest,
    ThreadSummary,
)
from assistant_web_backend.services.phoenix import PhoenixService
from assistant_web_backend.services.session_tree import (
    append_label_entry,
    append_message_entry,
    load_session_tree,
)
from assistant_web_backend.storage import MessageRecord, Storage

router = APIRouter(prefix="/api", tags=["threads"])

# Module-level Depends instance to satisfy B008 linter rule
_storage_dep = Depends(get_storage)


@router.get("/threads", response_model=ThreadListResponse)
def list_threads(storage: Storage = _storage_dep) -> ThreadListResponse:
    """List known threads from storage."""
    threads = storage.list_threads()
    return ThreadListResponse(
        threads=[
            ThreadSummary(
                remoteId=thread.remote_id,
                title=thread.title,
                status=thread.status,
            )
            for thread in threads
        ]
    )


@router.get("/threads/{remote_id}", response_model=ThreadDetailResponse)
def get_thread(remote_id: str, storage: Storage = _storage_dep) -> ThreadDetailResponse:
    """Get a single thread by ID."""
    thread = storage.fetch_thread(remote_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadDetailResponse(
        remoteId=thread.remote_id,
        title=thread.title,
        status=thread.status,
        createdAt=thread.created_at,
        updatedAt=thread.updated_at,
    )


@router.post("/threads", response_model=ThreadCreateResponse)
def create_thread(storage: Storage = _storage_dep) -> ThreadCreateResponse:
    """Create a new thread with a UUID4 identifier."""
    remote_id = str(uuid4())
    storage.create_thread(remote_id)
    return ThreadCreateResponse(remoteId=remote_id)


@router.patch("/threads/{remote_id}")
def rename_thread(
    remote_id: str, payload: ThreadRenameRequest, storage: Storage = _storage_dep
) -> dict[str, str]:
    """Rename a thread."""
    if not storage.fetch_thread(remote_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    storage.rename_thread(remote_id, payload.title)
    return {"status": "ok"}


@router.post("/threads/{remote_id}/archive")
def archive_thread(remote_id: str, storage: Storage = _storage_dep) -> dict[str, str]:
    """Archive a thread."""
    if not storage.fetch_thread(remote_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    storage.archive_thread(remote_id)
    return {"status": "ok"}


@router.post("/threads/{remote_id}/unarchive")
def unarchive_thread(remote_id: str, storage: Storage = _storage_dep) -> dict[str, str]:
    """Unarchive a thread."""
    if not storage.fetch_thread(remote_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    storage.unarchive_thread(remote_id)
    return {"status": "ok"}


@router.delete("/threads/{remote_id}")
def delete_thread(remote_id: str, storage: Storage = _storage_dep) -> dict[str, str]:
    """Delete a thread and its messages."""
    storage.delete_thread(remote_id)
    return {"status": "ok"}


@router.get("/threads/{remote_id}/messages", response_model=ThreadMessagesResponse)
def list_messages(remote_id: str, storage: Storage = _storage_dep) -> ThreadMessagesResponse:
    """List messages for a given thread."""
    if not storage.fetch_thread(remote_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = storage.list_messages(remote_id)
    return ThreadMessagesResponse(
        messages=[
            MessagePayload(
                id=record.message_id,
                role=record.role,
                content=record.content,
                createdAt=record.created_at,
                phoenixTraceId=record.phoenix_trace_id,
                phoenixTraceUrl=PhoenixService.build_trace_url(record.phoenix_trace_id)
                if record.phoenix_trace_id
                else None,
                phoenixSessionUrl=PhoenixService.build_session_url(record.phoenix_session_id)
                if record.phoenix_session_id
                else None,
                runProfile=record.run_profile,
                runMode=record.run_mode,
                executionMode=record.execution_mode,
                entrypointReference=record.entrypoint_reference,
                modelId=record.model_id,
                phoenixSessionId=record.phoenix_session_id,
                sessionEntryId=record.session_entry_id,
            )
            for record in messages
        ]
    )


@router.post("/threads/{remote_id}/messages")
def append_message(
    remote_id: str, payload: MessageAppendRequest, storage: Storage = _storage_dep
) -> dict[str, str]:
    """Append a message to a thread."""
    if not storage.fetch_thread(remote_id):
        storage.create_thread(remote_id)
    message = payload.message
    trace_id = payload.phoenix_trace_id or message.phoenix_trace_id
    try:
        session_entry_id = append_message_entry(
            remote_id,
            {
                "id": message.id,
                "role": message.role,
                "content": message.content,
                "createdAt": message.created_at,
                "runMode": payload.run_mode or message.run_mode,
                "executionMode": payload.execution_mode or message.execution_mode,
                "entrypointReference": payload.entrypoint_reference or message.entrypoint_reference,
                "modelId": payload.model_id or message.model_id,
            },
            entry_id=message.id,
            parent_entry_id=payload.parent_session_entry_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    storage.append_message(
        MessageRecord(
            message_id=message.id,
            thread_id=remote_id,
            role=message.role,
            content=message.content,
            created_at=message.created_at,
            phoenix_trace_id=trace_id,
            run_profile=payload.run_profile or message.run_profile,
            run_mode=payload.run_mode or message.run_mode,
            execution_mode=payload.execution_mode or message.execution_mode,
            entrypoint_reference=payload.entrypoint_reference or message.entrypoint_reference,
            model_id=payload.model_id or message.model_id,
            phoenix_session_id=payload.phoenix_session_id or message.phoenix_session_id,
            session_entry_id=session_entry_id,
        )
    )
    return {"status": "ok"}


@router.get("/threads/{remote_id}/session-tree", response_model=SessionTreeResponse)
def get_session_tree(remote_id: str, storage: Storage = _storage_dep) -> SessionTreeResponse:
    """Fetch the session tree for a thread."""
    if not storage.fetch_thread(remote_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    return load_session_tree(remote_id)


@router.post("/threads/{remote_id}/session-tree/label", response_model=SessionLabelResponse)
def label_session_entry(
    remote_id: str,
    payload: SessionLabelRequest,
    storage: Storage = _storage_dep,
) -> SessionLabelResponse:
    """Label a session entry for easier navigation."""
    if not storage.fetch_thread(remote_id):
        raise HTTPException(status_code=404, detail="Thread not found")
    try:
        label_entry_id = append_label_entry(remote_id, payload.entry_id, payload.label)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return SessionLabelResponse(status="ok", labelEntryId=label_entry_id)


def _title_from_messages(messages: list[MessagePayload]) -> str:
    """Generate a title from the first user message."""
    for message in messages:
        if message.role == "user":
            text = _text_from_parts(message.content)
            if text:
                return _trim_title(text)
    return "New chat"


def _text_from_parts(parts: list[dict]) -> str:
    """Extract text from content parts."""
    chunks: list[str] = []
    for part in parts:
        if part.get("type") == "text":
            text = part.get("text")
            if isinstance(text, str):
                chunks.append(text)
    return " ".join(chunks).strip()


def _trim_title(text: str) -> str:
    """Trim title to reasonable length."""
    trimmed = " ".join(text.split())
    if len(trimmed) <= 60:
        return trimmed
    return trimmed[:57].rstrip() + "..."


@router.post("/threads/{remote_id}/title", response_model=TitleResponse)
def generate_title(
    remote_id: str, payload: TitleRequest, storage: Storage = _storage_dep
) -> TitleResponse:
    """Generate and persist a thread title from messages."""
    if not storage.fetch_thread(remote_id):
        storage.create_thread(remote_id)
    title = _title_from_messages(payload.messages)
    storage.rename_thread(remote_id, title)
    return TitleResponse(title=title)
