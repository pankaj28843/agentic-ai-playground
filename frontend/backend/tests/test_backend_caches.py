"""Tests for backend caches."""

from __future__ import annotations

from types import SimpleNamespace

from assistant_web_backend.services import bedrock_metadata, resources


class DummyClient:
    def __init__(self) -> None:
        self.list_models_calls = 0
        self.list_profiles_calls = 0

    def list_foundation_models(self, **_kwargs):
        self.list_models_calls += 1
        return {"modelSummaries": [{"modelId": "bedrock.nova-lite"}]}

    def get_paginator(self, _name):
        self.list_profiles_calls += 1
        return SimpleNamespace(paginate=lambda: [{"inferenceProfileSummaries": []}])


def test_bedrock_overrides_cache(monkeypatch) -> None:
    bedrock_metadata.clear_bedrock_overrides_cache()
    dummy = DummyClient()
    monkeypatch.setattr(bedrock_metadata.boto3, "client", lambda *_args, **_kwargs: dummy)

    first = bedrock_metadata.fetch_bedrock_overrides()
    second = bedrock_metadata.fetch_bedrock_overrides()

    assert first.models == ["bedrock.nova-lite"]
    assert second.models == ["bedrock.nova-lite"]
    assert dummy.list_models_calls == 1
    assert dummy.list_profiles_calls == 1


def test_resources_cache(monkeypatch) -> None:
    resources.clear_resources_cache()

    load_calls = {"count": 0}

    class DummyLoader:
        def __init__(self, *args, **kwargs):
            pass

        def load(self):
            load_calls["count"] += 1
            return "bundle"

    monkeypatch.setattr(resources, "ResourceLoader", DummyLoader)
    monkeypatch.setattr(
        resources, "get_settings", lambda: SimpleNamespace(playground_config_dir=".")
    )

    assert resources.load_resources() == "bundle"
    assert resources.load_resources() == "bundle"
    assert load_calls["count"] == 1

    resources.clear_resources_cache()
    assert resources.load_resources() == "bundle"
    assert load_calls["count"] == 2
