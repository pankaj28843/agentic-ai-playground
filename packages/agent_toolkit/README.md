# Agent Toolkit

A reusable runtime toolkit for the Agentic AI Playground. The toolkit keeps agent
orchestration modular and testable by splitting configuration, tooling, and
execution into focused services.

## Architecture Overview

- **ConfigService**: Loads and validates config schema once, exposes cached snapshot.
- **ToolCatalog**: Expands tool groups and resolves tool callables.
- **ExecutionPipeline**: Orchestrates run/stream execution with minimal wiring.
- **AgentRuntime**: Thin facade used by the backend API and CLI tooling.

### Layering

- `config/` + `models/`: configuration types and schema loading.
- `tools/`: tool registry, MCP adapters, tool catalogs.
- `application/`: execution pipeline + tooling helpers.
- `runtime.py`: facade with telemetry setup and API surface.

## Quick Start

```python
from agent_toolkit import AgentRuntime

runtime = AgentRuntime()
result = runtime.run(
    mode="single",
    profile_name="default",
    prompt="Summarize the repo.",
    invocation_state={},
    session_id="demo",
)
print(result)
```

## Configuration

Configuration is loaded from the configured `PLAYGROUND_CONFIG_DIR` directory.
`ConfigService` centralizes the loader and validation results.

```python
from agent_toolkit import get_config_service

service = get_config_service()
snapshot = service.load_snapshot()
print(snapshot.validation.warnings)
```

## Tool Catalog

```python
from agent_toolkit import ToolCatalog, DEFAULT_TOOL_REGISTRY, get_config_service

catalog = ToolCatalog(DEFAULT_TOOL_REGISTRY, get_config_service())
selection = catalog.expand_tools("default")
print(selection.tools)
```
