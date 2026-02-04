"""Request context utilities for logging and tracing."""

from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import Request, Response

_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Return the current request id if set."""
    return _request_id_ctx.get()


def set_request_id(request_id: str | None) -> None:
    """Set the current request id."""
    _request_id_ctx.set(request_id)


def clear_request_id() -> None:
    """Clear the current request id."""
    _request_id_ctx.set(None)


async def request_id_middleware(request: Request, call_next: Callable) -> Response:
    """FastAPI middleware to inject request id into context and response headers."""
    request_id = request.headers.get("X-Request-Id") or str(uuid4())
    set_request_id(request_id)
    try:
        response = await call_next(request)
    finally:
        clear_request_id()
    response.headers["X-Request-Id"] = request_id
    return response
