"""Assistant Web Backend - FastAPI application.

This module provides the main FastAPI application with routes for:
- Thread management
- Message handling
- Chat streaming
- Configuration and health checks
"""

from __future__ import annotations

import logging
import os
import sys
import warnings

from agent_toolkit.telemetry import get_current_trace_id
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from assistant_web_backend.routes import chat_router, config_router, threads_router
from assistant_web_backend.services.phoenix import PhoenixService
from assistant_web_backend.services.request_context import (
    get_request_id,
    request_id_middleware,
)
from assistant_web_backend.services.runtime import get_runtime


def _allowed_origins() -> list[str]:
    allowed = os.getenv("WEB_ALLOWED_ORIGINS")
    if allowed:
        return [origin.strip() for origin in allowed.split(",") if origin.strip()]
    web_origin = os.getenv("WEB_ORIGIN")
    return [web_origin] if web_origin else []


# Suppress noisy OpenTelemetry context errors from Strands SDK async generators.
# These are non-fatal and occur when generators are garbage collected across contexts
# (Python 3.13 + async + contextvars issue in opentelemetry-python).
def _install_otel_error_filter() -> None:
    """Filter stderr to suppress known OpenTelemetry context detachment errors."""
    original_excepthook = sys.excepthook

    def filtered_excepthook(exc_type, exc_value, exc_tb):
        # Suppress ValueError from OpenTelemetry context detachment
        if exc_type is ValueError and "was created in a different Context" in str(exc_value):
            return
        if exc_type is ValueError and "generator already executing" in str(exc_value):
            return
        original_excepthook(exc_type, exc_value, exc_tb)

    sys.excepthook = filtered_excepthook

    # Also suppress the warnings
    warnings.filterwarnings("ignore", message=".*was created in a different Context.*")
    warnings.filterwarnings("ignore", message=".*generator already executing.*")


_install_otel_error_filter()

# Configure logging
logger = logging.getLogger("assistant_web_backend")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter("%(name)s - %(levelname)s - %(request_id)s - %(trace_id)s - %(message)s")
    )

    class _RequestIdFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:
            record.request_id = get_request_id() or "-"
            record.trace_id = get_current_trace_id() or "-"
            return True

    handler.addFilter(_RequestIdFilter())
    logger.addHandler(handler)

# Suppress noisy OpenTelemetry context errors from Strands SDK async generators
logging.getLogger("opentelemetry.context").setLevel(logging.CRITICAL)

# Create FastAPI app
app = FastAPI(title="Assistant Web Backend", version="1.0.0")
app.middleware("http")(request_id_middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Bootstrap services on application startup."""
    logger.info("Starting Assistant Web Backend...")

    # Bootstrap Phoenix project if enabled
    try:
        PhoenixService.bootstrap()
    except (RuntimeError, ValueError, OSError) as e:
        logger.warning("Phoenix bootstrap failed: %s", e)

    # Load runtime early to surface config validation warnings on boot
    try:
        get_runtime()
    except RuntimeError as e:
        logger.warning("Runtime bootstrap failed: %s", e)

    logger.info("Assistant Web Backend startup complete")


# Register routers
app.include_router(config_router)
app.include_router(threads_router)
app.include_router(chat_router)
