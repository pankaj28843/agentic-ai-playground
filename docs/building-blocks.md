# Agent Building Blocks

This document describes the composable architecture for agents, tools, and profiles in the Agentic AI Playground.

## Overview

The playground provides a declarative, configuration-driven approach to agent composition. Instead of hardcoding agent definitions in Python, you define them using TOML configuration files that support:

- **Tool Registry**: Centralized catalog of all available tools with metadata
- **Tool Groups**: Reusable collections of related tools
- **Agent Profiles**: Declarative agent definitions with inheritance
- **Graph/Swarm Templates**: Multi-agent orchestration patterns

## Tool Registry

The `ToolRegistry` provides a centralized catalog of tools with rich metadata.

### Tool Definition

Each tool has the following metadata:

| Field | Description |
|-------|-------------|
| `name` | Unique identifier for the tool |
| `description` | Human-readable description |
| `category` | Tool category (e.g., `techdocs`, `general`) |
| `tags` | Searchable tags |
| `input_schema` | JSON Schema for tool inputs |
| `output_schema` | JSON Schema for tool outputs |
| `capabilities` | Required capabilities (e.g., `read`, `write`, `mcp:techdocs`) |
| `requires_approval` | Whether tool calls need user approval |
| `source` | Tool origin (e.g., `local`, `agent:name`) |

### Registering Tools

Use the `@registered_tool` decorator to register tools with metadata:

```python
from agent_toolkit.tools import registered_tool

@registered_tool(
    name="my_tool",
    description="Does something useful",
    category="utilities",
    tags=["helper"],
    capabilities=["read"],
)
def my_tool(query: str) -> str:
    """Tool docstring used if description not provided."""
    return f"Result for {query}"
```

### Detail Levels

The registry supports progressive tool discovery with three detail levels:

- `name`: Tool name only (minimal context usage)
- `summary`: Name, description, category, tags, capabilities
- `full`: All metadata including schemas

### Browsing Tools

In the TUI, press `o` to open the Tool Browser screen, which displays:
- Tools organized by category
- Metadata table with capabilities and tags
- Full description with input/output schemas

## Tool Groups

Tool groups bundle related tools for easy reuse across profiles.

### Configuration

Define tool groups in `tool_groups.toml`:

```toml
[tool_groups.techdocs]
description = "TechDocs MCP tooling"
tools = ["techdocs_list_tenants", "techdocs_search", "techdocs_fetch"]
capabilities = ["read", "mcp:techdocs"]

[tool_groups.code_analysis]
description = "Code analysis tools"
tools = ["analyze_code", "find_references", "get_definitions"]
capabilities = ["read"]
```

## Agent Profiles

Agent profiles define reusable agent configurations with inheritance support.

### Profile Schema

| Field | Description |
|-------|-------------|
| `name` | Profile identifier |
| `description` | Human-readable description |
| `extends` | Parent profile to inherit from |
| `model` | Model ID (empty uses default) |
| `system_prompt` | Agent system prompt |
| `tools` | Explicit tool names |
| `tool_groups` | Tool group references |
| `metadata` | Custom metadata (owner, tags, etc.) |
| `constraints` | Runtime constraints (max_tool_calls, etc.) |

### Inheritance

Profiles can extend other profiles:

```toml
[profiles.base]
description = "Base profile"
tools = ["techdocs_list_tenants"]
metadata.owner = "playground"

[profiles.researcher]
extends = "base"
description = "Research agent"
tool_groups = ["techdocs"]
system_prompt = "You are a research assistant..."
```

The child profile inherits and merges:
- `tools`: Parent tools + child tools (deduplicated)
- `tool_groups`: Parent groups + child groups (deduplicated)
- `metadata`/`constraints`: Shallow merge (child overrides)
- Scalar fields: Child overrides parent

### Configuration Directory

Set `PLAYGROUND_CONFIG_DIR` to point at the directory containing your TOML files:

```bash
export PLAYGROUND_CONFIG_DIR=./config
```

The runtime loads config files from that directory at startup.

## Multi-Agent Templates

Graph and swarm patterns can be defined declaratively in config files.

### Graph Templates

Define in `graphs.toml`:

```toml
[graphs.research_pipeline]
entry_point = "research"
nodes = [
  { name = "research", profile = "techdocs_research" },
  { name = "analysis", profile = "general" },
  { name = "report", profile = "general" },
]
edges = [
  { from = "research", to = "analysis" },
  { from = "analysis", to = "report" },
]
timeouts.execution = 300
timeouts.node = 90
```

### Swarm Templates

Define in `swarms.toml`:

```toml
[swarms.collaborative]
entry_point = "researcher"
agents = [
  { name = "researcher", profile = "techdocs_research" },
  { name = "analyst", profile = "general" },
  { name = "reviewer", profile = "general" },
]
max_handoffs = 12
max_iterations = 12
timeouts.execution = 300
timeouts.node = 90
```

## Agent Factory

The `AgentFactory` constructs Strands agents from profiles:

```python
from agent_toolkit import AgentFactory, load_settings
from agent_toolkit.tools import DEFAULT_TOOL_REGISTRY

settings = load_settings()
factory = AgentFactory(settings=settings, registry=DEFAULT_TOOL_REGISTRY)

# Create from profile
agent = factory.create_from_profile(profile)

# Create specialist tool (agent-as-tool pattern)
tool = factory.create_specialist_tool_agent(
    name="specialist",
    description="Delegated task handler",
    system_prompt="Handle specialized queries.",
    tool_names=["techdocs_search"],
)
```

## Design Principles

### From Research

The architecture follows principles from:

- **12-Factor Agents**: Small, focused agents; tools as structured outputs
- **Strands SDK**: Agent composition; agents-as-tools pattern
- **Agentic Patterns**: Progressive tool discovery; capability compartmentalization

### Anti-Patterns Avoided

- Monolithic agents with broad tool access
- Hardcoded tool lists in code
- Leaky framework abstractions
- Hidden configuration defaults

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PLAYGROUND_CONFIG_DIR` | Config directory | `./config` |
| `BEDROCK_MODEL_ID` | Default model ID | `bedrock.nova-lite` |
| `TECHDOCS_MCP_URL` | TechDocs MCP endpoint | required |

### File Locations

| File | Description |
|------|-------------|
| `config/agents.toml` | Bundled agent profiles |
| `config/tool_groups.toml` | Bundled tool groups |
| `config/graphs.toml` | Graph templates |
| `config/swarms.toml` | Swarm templates |

---

## Related Documentation

- [Vision](vision.md) — Core philosophy and success criteria
- [Architecture Decisions](architecture/decisions.md) — Trade-offs and guiding principles
- [Operations](operations.md) — Debugging, exports, and CI expectations
- [Strands SDK Graph pattern](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/graph/)
- [Strands SDK Swarm pattern](https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/)
- [assistant-ui docs](https://www.assistant-ui.com/docs/)
