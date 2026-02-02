# Agentic AI Playground

Agentic AI Playground is a local-first environment for building and testing small, config-driven agents. It combines the Strands SDK orchestration layer, a FastAPI backend, and an assistant-ui React frontend, with TechDocs MCP as the default grounding source.

It is for engineers who want to prototype agent workflows, compare single/graph/swarm modes, and inspect traces without committing to a production stack. If you need a minimal, inspectable playground with clear configuration and reproducible runs, start here.

## Quick Start

```bash
# 1. Install dependencies
uv sync --all-packages
pnpm -C frontend install

# 2. Configure environment
cp .env.example .env
# Edit .env: set AWS credentials, TECHDOCS_MCP_URL, PLAYGROUND_CONFIG_DIR, WEB_ORIGIN,
# plus UVICORN_HOST/VITE_HOST for container binds.

# 3. Run the stack
uv run python scripts/restart_frontend_compose.py
```

Open the app at the origin you configured in `WEB_ORIGIN`.

## Configuration

All agent configuration lives in `./config/`:

| File | Purpose |
|------|---------|
| `agents.toml` | Atomic agent definitions (system prompt, model, tools) |
| `graphs.toml` | Graph orchestration templates (nodes, edges) |
| `swarms.toml` | Swarm templates (agents, handoffs, iterations) |
| `public_profiles.toml` | UI-visible modes mapping to entrypoints |
| `tool_groups.toml` | Tool group definitions with capabilities |

### Required Environment Variables

```bash
PLAYGROUND_CONFIG_DIR=./config
TECHDOCS_MCP_URL=https://techdocs.example.com/mcp
WEB_ORIGIN=https://app.example.com
WEB_ALLOWED_ORIGINS=
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=eu-central-1
BEDROCK_MODEL_ID=eu.amazon.nova-lite-v1:0
UVICORN_HOST=bind-host
VITE_HOST=bind-host
```

## Development

### Local dev (host tools)

```bash
# API server
uv run --package assistant-web-backend uvicorn assistant_web_backend.main:app --reload --port 10001

# Web app
pnpm -C frontend/apps/web dev --port 10000
```

### Docker dev (watch mode)

```bash
uv run python scripts/restart_frontend_compose.py --watch
```

### Testing

```bash
# Python lint + format
uv run ruff check . --fix
uv run ruff format .

# Python tests
uv run pytest packages/ -x -q

# Frontend lint + build
pnpm -C frontend lint
pnpm -C frontend build

# E2E tests (requires running stack)
source .env && uv run python scripts/e2e_tests.py
pnpm -C frontend exec playwright test --reporter=list
```

### Debug CLI

```bash
# Preflight check (TechDocs connectivity)
source .env && uv run python scripts/debug_tui_runtime.py --preflight

# Run agent query
source .env && uv run python scripts/debug_tui_runtime.py --prompt "list tenants"
```

## Non-goals and Limitations

- No authentication or multi-tenant security model.
- No backward compatibility guarantees (experimental playground).
- Not designed as a hosted or managed service.
- Production hardening is intentionally out of scope.

## Repo Structure

```
packages/agent_toolkit/     # Core runtime, tool adapters, config loader
frontend/
  apps/web/                 # React web app (assistant-ui)
  backend/                  # FastAPI backend
  packages/                 # Shared frontend packages
config/                     # TOML configuration files
docs/                       # Vision, architecture, operations
```

## Docs

- [Docs index](docs/README.md)
- [Vision](docs/vision.md)
- [Architecture decisions](docs/architecture/decisions.md)
- [Setup](docs/setup.md)
- [Operations](docs/operations.md)

## External References

- [Strands SDK documentation](https://strandsagents.com/latest/documentation/)
- [assistant-ui documentation](https://www.assistant-ui.com/docs/)

## Versioning

This is a pre-1.0 playground. Breaking changes are expected.

## Security

See `SECURITY.md` for reporting guidelines.

## License

Apache-2.0. See `LICENSE`.

## Contributing

See `CONTRIBUTING.md`.
