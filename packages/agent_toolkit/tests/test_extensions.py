from __future__ import annotations

from agent_toolkit.extensions import ExtensionRuntime
from agent_toolkit.tools.registry import ToolDefinition, ToolRegistry


def test_extension_event_emission_and_commands() -> None:
    registry = ToolRegistry()
    runtime = ExtensionRuntime(tool_registry=registry)

    def ext(api):
        api.on("before_tool", lambda payload: payload.get("tool"))
        api.register_command("hello", "Say hi", lambda _: "hi")

    runtime.load_extensions([("ext1", ext)])
    results = runtime.emit("before_tool", {"tool": "read"})
    assert results == ["read"]
    assert "hello" in runtime.commands


def test_extension_tool_registration() -> None:
    registry = ToolRegistry()
    runtime = ExtensionRuntime(tool_registry=registry)

    def ext(api):
        definition = ToolDefinition(name="t", description="tool")
        api.register_tool(definition, lambda: "ok")

    runtime.load_extensions([("ext2", ext)])
    assert registry.get("t") is not None


def test_extension_error_is_captured() -> None:
    registry = ToolRegistry()
    runtime = ExtensionRuntime(tool_registry=registry)

    def ext(api):
        def handler(_payload):
            raise RuntimeError("boom")

        api.on("event", handler)

    runtime.load_extensions([("ext3", ext)])
    runtime.emit("event", {})
    assert runtime.errors
    assert runtime.errors[0].message == "boom"
