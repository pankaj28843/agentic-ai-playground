# Agentic AI Playground Rules

## Project Summary
- **Web frontend is the primary UI** - The React-based web application is the main user interface.
- Built with Strands SDK for agent orchestration, assistant-ui for React components.
- uv workspace with `packages/agent_toolkit` (core library) and `frontend/backend` (FastAPI backend).
- TechDocs MCP is the primary grounding source for agent answers.

## Structure
- `packages/agent_toolkit`: core runtime, tool adapters, configuration, streaming.
- `frontend/`: React web application (primary UI)
  - `frontend/apps/web/`: Main web app with assistant-ui components
  - `frontend/backend/`: FastAPI backend serving the web UI
  - `frontend/packages/`: Shared frontend packages (api-client, assistant-runtime)
- `docs/`: vision, architecture decisions, and operational playbooks.

## AWS Credentials
- **Use `./.env` file** for AWS credentials in this project.
- The file contains `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`.
- Run `source ./.env` before any AWS commands or local debugging.
- The default `~/.aws/` credentials are NOT for this project.
- `scripts/setup_bedrock_iam.py` uses the default AWS profile for one-time IAM setup only.

## Development Conventions
- Use `uv run --package <name>` for commands tied to a workspace member.
- Keep UI logic in the app package; shared logic belongs in the toolkit.
- Prefer small, focused modules with explicit interfaces.
- Do not hard-code model IDs, MCP endpoints, or local paths in code; read from config or environment.
- **Debug workflow**: `source ./.env && uv run python scripts/debug_tui_runtime.py`
- Use `uv run python scripts/restart_frontend_compose.py` to manage the frontend Docker stack.
- **Never reference local paths or IP addresses in checked-in files.**

## Frontend Debugging
- Logs stream to `./logs/frontend/<date>/<service>_<timestamp>.log`
- Use `grep -r "ERROR" ./logs/frontend/` to find errors across all log files
- Each service (web, api) gets its own log file with Docker timestamps
- Snapshots of pre-restart logs are saved as `snapshot_*.log`

## Planning (PRP Methodology)
- For non-trivial changes, create a PRP (Product Requirement Prompt) plan.
- See `docs/PRP-README.md` for methodology and `docs/PRP-PLAN-TEMPLATE.md` for template.
- **Plan files live in `~/prp-plans/agentic-ai-playground/`, never checked in.**
- Use timestamped filenames: `<ISO-8601-timestamp>-<short-description>.md`
  - Generate timestamp with: `date -u +"%Y-%m-%dT%H:%M:%SZ"`
  - Example: `2026-01-07T22-47-21Z-coverage-95-ci-enforcement-plan.md`
- Plans should include: Goal/Why/Success Metrics, Current State, Implementation Blueprint, Validation Loop.

**⚠️ CRITICAL Planning Rules:**
- **All plans in ONE folder** (`~/prp-plans/agentic-ai-playground/`) — no exceptions
- **Always timestamp** — enables chronological reconstruction during debugging
- **Never create plans in the repo** — they clutter git history and get lost
- **Update plans as you work** — check off items, add discoveries, document decisions

## Quality Bar
- Use Ruff for linting/formatting.
- Add tests alongside new runtime logic.
- **Add E2E tests** when changing agent behavior, streaming, or UI interactions.
- Keep docs current with architecture decisions and trade-offs.
- Keep `README.md` and `docs/` in sync with code changes.

## Validation Loop (Before Push)

**Pre-commit hooks** (auto-installed via `uv run pre-commit install`):
- Ruff lint + format
- Trailing whitespace, YAML/TOML checks
- Bandit security scan

**Pre-push checks** (run `./scripts/pre-push-checks.sh` or let git hook run):
```bash
# Level 1: Python lint
uv run ruff check . --fix && uv run ruff format .

# Level 2: Python tests
uv run pytest packages/ -x -q

# Level 3: Frontend lint
pnpm -C frontend lint

# Level 4: Frontend build
pnpm -C frontend build
```

**E2E Tests (REQUIRED after agent/streaming/UI changes)**:
```bash
# Step 1: Clean Docker restart
uv run python scripts/restart_frontend_compose.py

# Step 2: Playwright E2E tests (UI, trace panel, tool visibility)
pnpm -C frontend exec playwright test --reporter=list

# Step 3: Python API E2E tests (tool execution, streaming format)
source .env && uv run python scripts/e2e_tests.py
```

**TUI E2E validation** (manual - costs money via Bedrock):
```bash
# Preflight check - verifies TechDocs MCP connectivity
source .env && uv run python scripts/debug_tui_runtime.py --preflight

# Full E2E - runs actual agent loop with Bedrock
source .env && uv run python scripts/debug_tui_runtime.py --prompt "list tenants (first 5)"
```

**Hook installation**:
```bash
uv run pre-commit install                      # pre-commit hooks
cp scripts/hooks/pre-push .git/hooks/pre-push  # pre-push hook
```

Fix all failures locally before pushing. CI will fail if these checks don't pass.

## Backward Compatibility
- **No backward compatibility required** for the playground app.
- This is an experimental playground - old threads/data can be deleted freely.
- Breaking changes to storage, API, or UI are acceptable.
- Focus on best UX and correctness over migration paths.

## Required References
- Always consult `docs/vision.md` and `docs/architecture/decisions.md` when making structural changes.
- Use TechDocs for external documentation (Strands SDK, assistant-ui, agentic patterns).
