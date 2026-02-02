"""Routes package for the assistant web backend API.

All API routes are defined here and registered with the FastAPI app.
"""

from assistant_web_backend.routes.chat import router as chat_router
from assistant_web_backend.routes.config import router as config_router
from assistant_web_backend.routes.threads import router as threads_router

__all__ = ["chat_router", "config_router", "threads_router"]
