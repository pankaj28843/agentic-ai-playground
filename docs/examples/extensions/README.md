# Extension Examples

These examples show how to wire extensions for the playground. They are intentionally small and can be adapted into your own runtime wiring.

## 1) Plan-mode gate
```python
from agent_toolkit.extensions import ExtensionRuntime
from agent_toolkit.tools.registry import ToolRegistry

runtime = ExtensionRuntime(tool_registry=ToolRegistry())

READ_ONLY_TOOLS = {"file_write", "editor"}

def plan_mode_extension(api):
    def guard(payload):
        tool_name = payload.get("tool", {}).get("name")
        if tool_name in READ_ONLY_TOOLS:
            return {"cancel": True, "reason": "Plan mode blocks writes"}
    api.on("tool_start", guard)

runtime.load_extensions([("plan-mode", plan_mode_extension)])
```

## 2) Permission gate
```python
from agent_toolkit.extensions import ExtensionRuntime
from agent_toolkit.tools.registry import ToolRegistry

runtime = ExtensionRuntime(tool_registry=ToolRegistry())

ALLOWED = {"techdocs.search", "techdocs.fetch"}

def permission_gate(api):
    def guard(payload):
        tool_name = payload.get("tool", {}).get("name")
        if tool_name not in ALLOWED:
            return {"cancel": True, "reason": "Tool not allowlisted"}
    api.on("tool_start", guard)

runtime.load_extensions([("gate", permission_gate)])
```

## 3) Custom summary injector
```python
from agent_toolkit.extensions import ExtensionRuntime
from agent_toolkit.tools.registry import ToolRegistry

runtime = ExtensionRuntime(tool_registry=ToolRegistry())

def summary_extension(api):
    def on_compaction(payload):
        summary = payload.get("summary", "")
        api.register_command("last_summary", "Get last summary", lambda _: summary)
    api.on("compaction", on_compaction)

runtime.load_extensions([("summary", summary_extension)])
```

## 4) Subagent coordinator
```python
from agent_toolkit.extensions import ExtensionRuntime
from agent_toolkit.tools.registry import ToolRegistry

runtime = ExtensionRuntime(tool_registry=ToolRegistry())

def subagent_extension(api):
    api.register_command(
        "delegate",
        "Invoke subagent tool",
        lambda prompt: f"Run subagent with: {prompt}",
    )

runtime.load_extensions([("subagent", subagent_extension)])
```
