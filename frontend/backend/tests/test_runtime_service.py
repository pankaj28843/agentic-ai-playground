"""Tests for runtime provider caching behavior."""

from assistant_web_backend.services import runtime as runtime_module


def test_runtime_provider_singleton(monkeypatch) -> None:
    class DummyRuntime:
        init_count = 0

        def __init__(self) -> None:
            type(self).init_count += 1

    monkeypatch.setattr(runtime_module, "_load_runtime_class", lambda: DummyRuntime)
    runtime_module.get_runtime.cache_clear()

    runtime_one = runtime_module.get_runtime()
    runtime_two = runtime_module.get_runtime()

    assert runtime_one is runtime_two
    assert DummyRuntime.init_count == 1
    assert runtime_module.is_available() is True
