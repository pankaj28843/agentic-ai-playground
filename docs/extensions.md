# Extensions & Hooks

Extensions let you add tools, hook into runtime events, and register commands without modifying core runtime code.

## Architecture
- `ExtensionRuntime` loads extension factories and manages event emission.
- `ExtensionAPI` exposes `on()`, `register_tool()`, and `register_command()`.
- `ExtensionRegistry` stores event handlers and isolates errors per extension.

## Common events
- `agent_start`, `turn_start`, `tool_start`, `tool_end`, `turn_end`, `agent_end`
- Custom events can be emitted by runtime modules and extensions.

## Example usage
```python
from agent_toolkit.extensions import ExtensionRuntime
from agent_toolkit.tools.registry import ToolRegistry, ToolDefinition

runtime = ExtensionRuntime(tool_registry=ToolRegistry())

def example_extension(api):
    api.on("turn_start", lambda payload: print("turn start", payload))
    api.register_command("ping", "Emit a ping", lambda _: "pong")

runtime.load_extensions([("example", example_extension)])
```

## Best practices
- Keep extensions small and focused; prefer composition over mutation.
- Use hooks to enforce safety/approval policies rather than hardcoding them.
- Emit custom session entries for UI traceability.
