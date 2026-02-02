# Setup

## Prereqs
- Python 3.14
- uv
- AWS CLI configured for Bedrock access
- botocore[crt] (installed via `uv sync --all-packages`)

## Install
```
uv sync --all-packages
```

The app loads `.env` automatically on startup.
Set `PLAYGROUND_CONFIG_DIR` to the directory that contains your TOML configuration files.

## Run the Textual app
```
uv run --package agent-playground-app agent-playground-app
```

## Web playground (Assistant UI)

### Local dev
```
pnpm -C frontend install
uv run --package assistant-web-backend uvicorn assistant_web_backend.main:app --reload --port 10001
pnpm -C frontend/apps/web dev --port 10000
```

> **Security note:** The API is unauthenticated. Keep it bound to loopback by default and only expose it on trusted networks.

### Docker dev (watch mode)
```
uv run python scripts/restart_frontend_compose.py
```

Options:
- `--watch` / `-w`: Enable live reload (foreground)
- `--no-build`: Skip image rebuild
- `--logs` / `-l`: Follow logs in terminal after starting
- `--down-only`: Stop the stack without restarting
- `--no-log-stream`: Disable log file streaming
- `--verbose` / `-v`: Show detailed output
- `--dry-run`: Preview commands without executing

Docker Compose watch requires v2.23.0+ (sync+restart rules). Older versions run without watch.

### Frontend logs
Logs stream to `./logs/frontend/<date>/<service>_<timestamp>.log`:

```
./logs/frontend/
└── 2026-01-26/
    ├── web_11-04-21.log      # Web container logs
    ├── api_11-04-21.log      # API container logs
    └── snapshot_11-03-30.log # Pre-restart snapshot
```

Debug with grep:
```
grep -r "ERROR" ./logs/frontend/
tail -f ./logs/frontend/$(date +%Y-%m-%d)/*.log
```

Old logs are pruned automatically (default: 14 days). Override with `--log-retention-days`.

### Web environment variables
- `VITE_API_BASE_URL` (blank means same-origin API calls in compose)
- `WEB_ORIGIN` (required; public origin allowed by the API CORS policy)
- `WEB_ALLOWED_ORIGINS` (optional comma-separated list; overrides `WEB_ORIGIN`)
- `WEB_STORAGE_DIR` (default `.data`, compose persists in `.data/assistant-web`)
- `WEB_STRANDS_PROFILE=<profile>` to enable Strands-backed responses
- `UVICORN_HOST` (bind host for API container)
- `VITE_HOST` (bind host for web container)
- `E2E_BASE_URL` (base URL for Playwright and API e2e tests)
- `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY` (required for real Bedrock calls in the API container)

## Non-interactive debug
Run the non-interactive debug script to exercise the runtime without the TUI:

```
uv run python scripts/debug_tui_runtime.py --prompt "list tenants (first 10)" --preflight
```

## TechDocs MCP
Provide a TechDocs MCP endpoint via environment variable:

```
export TECHDOCS_MCP_URL="https://techdocs.example.com/mcp"
```

## Bedrock configuration
Set the Bedrock region and model ID to an enabled on-demand model:

```
export AWS_REGION="eu-central-1"
export BEDROCK_MODEL_ID="eu.amazon.nova-micro-v1:0"
```

The runtime uses `BEDROCK_MODEL_ID` for all profiles unless overridden.

## Default run mode
Set a default run mode for the TUI (public profile id from `config/public_profiles.toml`):

```
export RUN_MODE="quick"
```

## Stream timeout
Control how long the TUI waits for stream events before reporting a timeout:

```
export SINGLE_EXECUTION_TIMEOUT="120"
```


## Bedrock
If you see a `MissingDependencyException`, install dependencies with:

```
uv sync --all-packages
```

If Bedrock returns `ResourceNotFoundException`, request access for the configured model or
set `BEDROCK_MODEL_ID` to a model that is enabled for the account.
