"""Configuration and health routes."""

from __future__ import annotations

from agent_toolkit.config import load_settings
from agent_toolkit.config.new_loader import NewConfigLoader
from agent_toolkit.providers import load_providers
from fastapi import APIRouter, HTTPException

from assistant_web_backend.models.config import (
    InferenceProfileSummary,
    PhoenixConfigResponse,
    ProfileDefaults,
    SettingsResponse,
    ToolGroupSummary,
)
from assistant_web_backend.models.profiles import ProfilesResponse, ProfileSummary
from assistant_web_backend.models.resources import (
    PromptResource,
    ResourceDiagnostics,
    ResourcesResponse,
    SkillResource,
)
from assistant_web_backend.services.bedrock_metadata import fetch_bedrock_overrides
from assistant_web_backend.services.phoenix import PhoenixService
from assistant_web_backend.services.resources import load_resources
from assistant_web_backend.services.runtime import RuntimeService

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
        runtime = RuntimeService.get_runtime()
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


@router.get("/resources", response_model=ResourcesResponse)
def list_resources() -> ResourcesResponse:
    """List available skills and prompt templates."""
    bundle = load_resources()
    return ResourcesResponse(
        skills=[
            SkillResource(
                name=skill.name,
                description=skill.description,
                content=skill.content,
                source=skill.source,
            )
            for skill in bundle.skills
        ],
        prompts=[
            PromptResource(
                name=prompt.name,
                description=prompt.description,
                content=prompt.content,
                source=prompt.source,
            )
            for prompt in bundle.prompts
        ],
        diagnostics=ResourceDiagnostics(warnings=bundle.diagnostics.warnings),
    )


@router.get("/settings", response_model=SettingsResponse)
def list_settings() -> SettingsResponse:
    """List settings metadata for the UI (models, tool groups, defaults)."""
    loader = NewConfigLoader()
    schema, validation = loader.load()
    registry = load_providers()
    settings = load_settings()
    bedrock_overrides = fetch_bedrock_overrides()
    models = bedrock_overrides.models or sorted(registry.list_models())

    tool_groups = [
        ToolGroupSummary(
            name=group.name,
            description=group.description,
            tools=list(group.tools),
            capabilities=list(group.capabilities),
        )
        for group in schema.tool_groups.values()
    ]
    profile_defaults: list[ProfileDefaults] = []
    for profile_id, profile in schema.public_profiles.items():
        tool_groups_for_profile: list[str] = []
        model = None
        if profile.entrypoint_type == "single":
            agent = schema.agents.get(profile.entrypoint_reference)
            if agent:
                tool_groups_for_profile = list(agent.tool_groups)
                model = agent.model
        profile_defaults.append(
            ProfileDefaults(
                profileId=profile_id,
                model=model,
                toolGroups=tool_groups_for_profile,
            )
        )

    return SettingsResponse(
        models=models,
        defaultModel=settings.bedrock_model_id,
        toolGroups=sorted(tool_groups, key=lambda g: g.name),
        profileDefaults=sorted(profile_defaults, key=lambda p: p.profile_id),
        inferenceProfiles=[
            InferenceProfileSummary(
                inferenceProfileId=profile.inference_profile_id,
                inferenceProfileArn=profile.inference_profile_arn,
                name=profile.name,
                status=profile.status,
                type=profile.type,
            )
            for profile in bedrock_overrides.inference_profiles
        ],
        warnings=validation.warnings + bedrock_overrides.warnings,
    )
