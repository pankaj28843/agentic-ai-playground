from __future__ import annotations


def test_settings_api_returns_models_and_tool_groups(client, monkeypatch) -> None:
    from assistant_web_backend.routes import config as config_module
    from assistant_web_backend.services.bedrock_metadata import BedrockOverrides

    monkeypatch.setattr(
        config_module,
        "fetch_bedrock_overrides",
        lambda: BedrockOverrides(models=[], inference_profiles=[], warnings=[]),
    )

    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()

    models = payload.get("models", [])
    assert "bedrock.nova-lite" in models

    tool_groups = {group["name"] for group in payload.get("toolGroups", [])}
    assert "techdocs" in tool_groups

    profile_defaults = {profile["profileId"] for profile in payload.get("profileDefaults", [])}
    assert "quick" in profile_defaults


def test_settings_api_includes_inference_profiles(client, monkeypatch) -> None:
    from assistant_web_backend.routes import config as config_module
    from assistant_web_backend.services.bedrock_metadata import (
        BedrockInferenceProfile,
        BedrockOverrides,
    )

    monkeypatch.setattr(
        config_module,
        "fetch_bedrock_overrides",
        lambda: BedrockOverrides(
            models=["bedrock.nova-lite"],
            inference_profiles=[
                BedrockInferenceProfile(
                    inference_profile_id="profile-1",
                    inference_profile_arn="arn:aws:bedrock:eu-central-1:123:inference-profile/profile-1",
                    name="Test Profile",
                    status="ACTIVE",
                    type="ON_DEMAND",
                )
            ],
            warnings=[],
        ),
    )

    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()
    profiles = payload.get("inferenceProfiles", [])
    assert profiles[0]["inferenceProfileId"] == "profile-1"
