from __future__ import annotations


def test_settings_api_returns_models_and_tool_groups(client) -> None:
    response = client.get("/api/settings")
    assert response.status_code == 200
    payload = response.json()

    models = payload.get("models", [])
    assert "bedrock.nova-lite" in models

    tool_groups = {group["name"] for group in payload.get("toolGroups", [])}
    assert "techdocs" in tool_groups

    profile_defaults = {profile["profileId"] for profile in payload.get("profileDefaults", [])}
    assert "quick" in profile_defaults
