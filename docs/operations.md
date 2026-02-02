# Operations

## GitHub Hygiene
- Public repository with `main` as default branch.
- Enable Dependabot and required status checks when CI is configured.
- Keep labels and issue templates minimal and task-oriented.

## OpenCode
- Project config lives in `opencode.json`.
- Project config is instruction-only (see `opencode.json`).
- Instructions come from `AGENTS.md`, `docs/README.md`, `docs/vision.md`, and `docs/architecture/decisions.md`.
- Model and MCP settings are configured in global or remote OpenCode config, not in the project file.

## Run Exports
- Use the `x` key in the TUI to export runs to `.exports/<timestamp>`.
- Exports include snapshots, `summary.md`, and evaluation reports.

## Debugging
- Use `uv run python scripts/debug_tui_runtime.py --prompt "list tenants (first 10)" --preflight` to reproduce runtime behavior without the TUI.
- The script prints `[trace]` lines for tool usage and tool output.

## TechDocs Troubleshooting
- TUI preflight logs report TechDocs MCP readiness in the tool log on startup.
- If tool calls fail, verify `TECHDOCS_MCP_URL` and confirm the server exposes `root_search` and `root_fetch` tools.

## Bedrock Troubleshooting
- If you see `ResourceNotFoundException`, request access for the configured model or set `BEDROCK_MODEL_ID`.
- Verify AWS region and model access with `aws bedrock list-foundation-models`.

## CI Expectations
- Run `uv run ruff check . --fix && uv run ruff format .`.
- Run `uv run pytest packages/ -x -q`.
- Run `pnpm -C frontend lint` and `pnpm -C frontend build`.
- After agent/UI changes, run Playwright and API e2e tests.

---

## Related Documentation

- [Vision](vision.md) — Core philosophy and success criteria
- [Architecture Decisions](architecture/decisions.md) — Trade-offs and guiding principles
- [Building Blocks](building-blocks.md) — Tool registry, profiles, and factory APIs
