"""Configuration and health routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from assistant_web_backend.models.config import PhoenixConfigResponse
from assistant_web_backend.models.profiles import ProfilesResponse, ProfileSummary
from assistant_web_backend.services.phoenix import PhoenixService
from assistant_web_backend.services.runtime import get_runtime

router = APIRouter(prefix="/api", tags=["config"])


@router.get("/health")
def health() -> dict[str, str]:
    """Simple health check for the web API."""
    return {"status": "ok"}


@router.get("/phoenix", response_model=PhoenixConfigResponse)
def get_phoenix_config() -> PhoenixConfigResponse:
    """Get Phoenix observability configuration for frontend deep links."""
    return PhoenixService.get_config()


@router.get("/profiles", response_model=ProfilesResponse)
def list_profiles() -> ProfilesResponse:
    """List available profiles and run modes for the runtime."""
    # Get runtime first
    try:
        runtime = get_runtime()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    public_profiles = runtime.list_public_profiles()
    if not public_profiles:
        raise HTTPException(status_code=500, detail="No public profiles configured")

    run_modes = [profile["id"] for profile in public_profiles]
    default_run_mode = next(
        (profile["id"] for profile in public_profiles if profile.get("default")), None
    )
    if not default_run_mode and run_modes:
        default_run_mode = run_modes[0]

    return ProfilesResponse(
        profiles=[
            ProfileSummary(
                id=profile["id"],
                name=profile.get("display_name", profile["id"]),
                description=profile.get("description"),
                entrypoint_type=profile.get("entrypoint_type"),
                entrypoint_reference=profile.get("entrypoint_reference"),
                default=bool(profile.get("default")),
                metadata=profile.get("metadata", {}),
            )
            for profile in public_profiles
        ],
        runModes=run_modes,
        defaultRunMode=default_run_mode,
    )
