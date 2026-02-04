"""Tests for runtime service singleton behavior."""

from assistant_web_backend.services import runtime as runtime_module


def test_runtime_service_singleton(monkeypatch) -> None:
    class DummyRuntime:
        init_count = 0

        def __init__(self) -> None:
            type(self).init_count += 1

    monkeypatch.setattr(runtime_module, "AgentRuntime", DummyRuntime)
    monkeypatch.setattr(runtime_module, "_runtime", None)

    runtime_one = runtime_module.RuntimeService.get_runtime()
    runtime_two = runtime_module.RuntimeService.get_runtime()

    assert runtime_one is runtime_two
    assert DummyRuntime.init_count == 1
    assert runtime_module.RuntimeService.is_available() is True
