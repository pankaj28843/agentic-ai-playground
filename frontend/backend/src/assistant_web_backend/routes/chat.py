"""Chat streaming routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from assistant_web_backend.dependencies import get_storage
from assistant_web_backend.models.threads import ChatRunRequest
from assistant_web_backend.services.chat_runner import stream_chat
from assistant_web_backend.storage import Storage

router = APIRouter(prefix="/api", tags=["chat"])
_storage_dep = Depends(get_storage)


@router.post("/chat/run")
def run_chat(payload: ChatRunRequest, storage: Storage = _storage_dep) -> StreamingResponse:
    """Stream a chat response for the provided messages."""
    thread_id = payload.thread_id or ""

    async def stream():
        async for chunk in stream_chat(thread_id, payload, storage):
            yield chunk

    return StreamingResponse(stream(), media_type="application/jsonl")
