# Debugging Workflow

## Non-interactive runtime debug

Use `scripts/debug_tui_runtime.py` to exercise the same runtime path as the TUI without any UI input.
The script streams tool traces and responses to the terminal and helps confirm TechDocs + Bedrock end-to-end behavior.

### Prereqs
- `TECHDOCS_MCP_URL` set
- `AWS_REGION` and `BEDROCK_MODEL_ID` set
- Dependencies installed: `uv sync --all-packages`

### Run a quick smoke
```bash
uv run python scripts/debug_tui_runtime.py --prompt "list tenants (first 10)" --preflight
```

### Common options
```bash
# Use a different profile
uv run python scripts/debug_tui_runtime.py --profile techdocs_research --prompt "list tenants (first 10)"

# Run without streaming (single-shot)
uv run python scripts/debug_tui_runtime.py --no-stream --prompt "list tenants (first 10)"

# Override mode or session/resource
uv run python scripts/debug_tui_runtime.py --mode swarm --session demo --resource "file://<path-to-doc>"

# List tenants in batches
uv run python scripts/debug_tui_runtime.py --prompt "list tenants, limit 50"
```

### Output expectations
- `[trace] working...` prints immediately so you know the run started.
- Tool usage and tool output appear as `[trace]` lines.
- The final answer streams inline; if nothing returns, a fallback message appears.
- Large prompts (like "list all docs") can exhaust model tokens; prefer constrained prompts.
- Use `SINGLE_EXECUTION_TIMEOUT` to adjust how long the TUI waits before surfacing a timeout.

## Frontend debugging

### Managing the frontend stack
Use the restart script to manage the Docker Compose stack:

```bash
# Start in daemon mode (default) with log streaming
uv run python scripts/restart_frontend_compose.py

# Start with live reload for development
uv run python scripts/restart_frontend_compose.py --watch

# Start and follow logs in terminal
uv run python scripts/restart_frontend_compose.py --logs

# Stop the stack
uv run python scripts/restart_frontend_compose.py --down-only

# Preview commands without executing
uv run python scripts/restart_frontend_compose.py --dry-run --verbose
```

### Frontend log structure
Logs are automatically streamed to `./logs/frontend/` organized by date:

```
./logs/frontend/
└── 2026-01-26/
    ├── web_11-04-21.log      # Web container (Vite dev server)
    ├── api_11-04-21.log      # API container (FastAPI/Uvicorn)
    ├── web_11-08-37.log      # New log file after restart
    ├── api_11-08-37.log
    └── snapshot_11-03-30.log # Pre-restart log snapshot
```

Each restart creates new timestamped log files. Snapshots capture logs before containers are stopped.

### Debugging frontend issues
```bash
# Find errors across all frontend logs
grep -r "ERROR" ./logs/frontend/

# Find specific HTTP errors
grep -r "500\|502\|503" ./logs/frontend/

# Watch latest web logs
tail -f ./logs/frontend/$(date +%Y-%m-%d)/web_*.log

# Watch latest API logs
tail -f ./logs/frontend/$(date +%Y-%m-%d)/api_*.log

# Watch all latest logs
tail -f ./logs/frontend/$(date +%Y-%m-%d)/*.log

# Search for specific request patterns
grep -r "POST /api/chat" ./logs/frontend/

# Find Python tracebacks in API logs
grep -A 10 "Traceback" ./logs/frontend/*/api_*.log
```

### Log retention
Old logs are pruned automatically on each restart (default: 14 days).

```bash
# Change retention period
uv run python scripts/restart_frontend_compose.py --log-retention-days 7

# Skip pruning
uv run python scripts/restart_frontend_compose.py --skip-log-prune

# Use custom log directory
uv run python scripts/restart_frontend_compose.py --log-dir ./logs/custom
```

### Disabling log streaming
If you don't need persistent log files:

```bash
uv run python scripts/restart_frontend_compose.py --no-log-stream
```

Logs are still available via `docker compose logs -f` when streaming is disabled.
