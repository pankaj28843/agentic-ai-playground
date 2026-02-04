"""Phoenix observability service.

Handles Phoenix configuration, project ID caching, and URL generation.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from assistant_web_backend.models.config import PhoenixConfigResponse
from assistant_web_backend.services.settings import get_settings

logger = logging.getLogger(__name__)

# Cache Phoenix project ID to avoid repeated API calls
_phoenix_project_id_cache: dict[str, str] = {}


def _fetch_phoenix_project_id(base_url: str, project_name: str) -> str | None:
    """Fetch Phoenix project ID by name using REST API."""
    try:
        # Use the correct endpoint: /v1/projects/{project_identifier}
        # Project identifier can be the project name
        url = f"{base_url}/v1/projects/{project_name}"
        with urllib.request.urlopen(url, timeout=5) as response:  # noqa: S310
            data = json.loads(response.read().decode())
            # Handle both direct response and nested data structure
            if "data" in data:
                return data["data"].get("id")
            return data.get("id")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            logger.debug("Phoenix project '%s' not found", project_name)
        else:
            logger.debug("HTTP error fetching Phoenix project ID: %s", e)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        logger.debug("Could not fetch Phoenix project ID from %s: %s", base_url, e)
    return None


def _create_phoenix_project(base_url: str, project_name: str) -> str | None:
    """Create a new Phoenix project and return its ID."""
    try:
        url = f"{base_url}/v1/projects"
        data = json.dumps({"name": project_name}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})  # noqa: S310
        with urllib.request.urlopen(req, timeout=5) as response:  # noqa: S310
            result = json.loads(response.read().decode())
            project_id = result["data"].get("id") if "data" in result else result.get("id")
            logger.info("Created Phoenix project '%s' with ID: %s", project_name, project_id)
            return project_id
    except urllib.error.HTTPError as e:
        if e.code == 409:
            logger.debug("Phoenix project '%s' already exists", project_name)
            # Try to fetch the existing project
            return _fetch_phoenix_project_id(base_url, project_name)
        logger.warning("HTTP error creating Phoenix project: %s", e)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
        logger.warning("Could not create Phoenix project: %s", e)
    return None


def _get_or_create_phoenix_project(base_url: str, project_name: str) -> str | None:
    """Get existing Phoenix project or create it if it doesn't exist."""
    # Try to fetch existing project first
    project_id = _fetch_phoenix_project_id(base_url, project_name)
    if project_id:
        return project_id

    # Create project if it doesn't exist
    return _create_phoenix_project(base_url, project_name)


class PhoenixService:
    """Service for Phoenix observability integration."""

    # Cached settings for URL building (set during bootstrap)
    _public_url: str | None = None
    _collector_url: str | None = None
    _project_id: str | None = None

    @classmethod
    def bootstrap(cls) -> None:
        """Bootstrap Phoenix project on application startup."""
        settings = get_settings()
        if not settings.phoenix_enabled:
            logger.debug("Phoenix not enabled, skipping bootstrap")
            return

        project_name = settings.phoenix_project_name or "default"
        base_url = settings.phoenix_collector_endpoint or ""

        if not base_url:
            logger.warning("Phoenix enabled but no collector endpoint configured")
            return

        logger.info("Bootstrapping Phoenix project: %s", project_name)

        # Get or create project and cache the ID
        cache_key = f"{base_url}:{project_name}"
        project_id = _get_or_create_phoenix_project(base_url, project_name)

        if project_id:
            _phoenix_project_id_cache[cache_key] = project_id
            # Cache for URL building
            cls._collector_url = base_url
            cls._public_url = settings.phoenix_public_url or base_url
            cls._project_id = project_id
            logger.info(
                "Phoenix project ready: %s (ID: %s, public URL: %s)",
                project_name,
                project_id,
                cls._public_url,
            )
        else:
            logger.warning("Failed to bootstrap Phoenix project: %s", project_name)

    @classmethod
    def get_config(cls) -> PhoenixConfigResponse:
        """Build Phoenix configuration from settings."""
        settings = get_settings()
        if not settings.phoenix_enabled:
            return PhoenixConfigResponse(enabled=False)

        project_name = settings.phoenix_project_name or "default"
        base_url = settings.phoenix_collector_endpoint or ""

        # Use cached project ID (should be available after bootstrap)
        cache_key = f"{base_url}:{project_name}"
        project_id = _phoenix_project_id_cache.get(cache_key)

        # If not cached, try to fetch it (fallback for cases where bootstrap wasn't called)
        if not project_id:
            project_id = _get_or_create_phoenix_project(base_url, project_name)
            if project_id:
                _phoenix_project_id_cache[cache_key] = project_id
                cls._collector_url = base_url
                cls._public_url = settings.phoenix_public_url or base_url
                cls._project_id = project_id

        # Return public URL for frontend to display (not collector endpoint)
        public_url = settings.phoenix_public_url or base_url

        return PhoenixConfigResponse(
            enabled=True,
            baseUrl=public_url,
            projectName=project_name,
            projectId=project_id,
        )

    @classmethod
    def build_trace_url(cls, trace_id: str) -> str | None:
        """Build a deep link URL to a specific trace in Phoenix.

        Uses project_id (base64 encoded) for the URL path as Phoenix expects.
        Returns None if Phoenix is not configured.
        """
        if not cls._public_url or not cls._project_id:
            # Try to initialize from settings if not bootstrapped
            settings = get_settings()
            if not settings.phoenix_enabled:
                return None
            cls._public_url = settings.phoenix_public_url or settings.phoenix_collector_endpoint
            # Try to get project ID
            cache_key = f"{settings.phoenix_collector_endpoint}:{settings.phoenix_project_name}"
            cls._project_id = _phoenix_project_id_cache.get(cache_key)
            if not cls._project_id:
                return None

        return f"{cls._public_url}/projects/{cls._project_id}/traces/{trace_id}"

    @classmethod
    def build_session_url(cls, session_id: str) -> str | None:
        """Build a deep link URL to session traces in Phoenix.

        Returns None if Phoenix is not configured.
        """
        if not cls._public_url or not cls._project_id:
            # Try to initialize from settings if not bootstrapped
            settings = get_settings()
            if not settings.phoenix_enabled:
                return None
            cls._public_url = settings.phoenix_public_url or settings.phoenix_collector_endpoint
            cache_key = f"{settings.phoenix_collector_endpoint}:{settings.phoenix_project_name}"
            cls._project_id = _phoenix_project_id_cache.get(cache_key)
            if not cls._project_id:
                return None

        return f"{cls._public_url}/projects/{cls._project_id}/sessions?sessionId={session_id}"
