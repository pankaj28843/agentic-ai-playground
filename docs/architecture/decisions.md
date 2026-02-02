# Architecture Decision Log

Record architecture trade-offs and revisit decisions regularly. Keep entries short, explicit, and dated.

---

## Guiding Principles

These principles inform all architectural decisions (see also [vision.md](../vision.md)):

1. **Small, focused agents**: Prefer multiple specialized agents over monolithic ones.
2. **Emergent behavior**: Let agents discover solutions; avoid over-prescribing workflows.
3. **Context hygiene**: Compartmentalize state; protect context windows from pollution.
4. **Composability over complexity**: Declarative config; plug-and-play patterns.
5. **Refactor for maintainability**: Favor readable, testable code over clever abstractions.

---

## Decision Log

### 2026-01-30: Strands SDK Enrichment
- **Decision**: Complete Strands SDK enrichment with multi-provider support, Pydantic models, and tool/eval integration.
- **Rationale**: Strands SDK supports 12+ model providers (Bedrock, Anthropic, OpenAI, Ollama, Gemini, etc.). Current implementation was limited to Bedrock with hardcoded model IDs. SDK provides 45+ pre-built tools and evaluation framework.
- **Changes Implemented**:
  - Migrated core configuration models (Settings, AgentProfile, ConfigSchema, ProviderConfig, ModelConfig) to Pydantic with `frozen=True` for immutability
  - Created `providers/` package with `ModelProviderRegistry` supporting Bedrock, Anthropic, OpenAI, Ollama
  - Added `config/providers.toml` for declarative model configuration
  - Created `strands_tools` adapter with 30+ tools mapped to registry
  - Added `strands_evals` types (`EvalRunner`, `EvalCase`, `EvalConfig`) for programmatic evaluation
  - Enhanced multiagent templates with `model_override` support per node/agent
- **Trade-offs**: Additional config files and abstractions; lazy imports for optional providers; adapter layer for tool registry integration.

### 2026-01-29
- **Decision**: Adopt comprehensive system prompt patterns based on analysis of 40+ AI tool prompts and agentic patterns research.
- **Rationale**: Implement tool authenticity, parallel execution, progressive disclosure, and context hygiene patterns to achieve 3-5x performance improvement and eliminate anti-patterns like tool role-playing.
- **Trade-offs**: More complex prompt structure but significantly improved consistency, performance, and maintainability across all agent profiles.

### 2026-01-28
- **Decision**: Adopt agent-native mindset for all refactors—prefer emergent behavior, rich feedback loops, and context compartmentalization.
- **Rationale**: Aligns with TechDocs patterns (Oracle/Worker, progressive disclosure, 12-Factor Agents).
- **Trade-offs**: Requires discipline to avoid over-engineering; may add orchestration complexity.

### 2026-01-28
- **Decision**: Move web UI styling to CSS Modules with cascade layers; keep only tokens/resets in global base and leave an explicit overrides layer.
- **Rationale**: Co-located styles reduce cross-component leakage and make future UI scaling safer after recent resize/scroll regressions.
- **Trade-offs**: More files and explicit class wiring; requires `:global` selectors for theme-aware overrides.

### 2026-01-26
- **Decision**: Implement composable agent building blocks with ToolRegistry, configuration loaders, and AgentFactory.
- **Rationale**: Enable configuration-driven agent composition without code changes; support inheritance, tool groups, and templates.
- **Trade-offs**: Added complexity in config loading; TOML-only for now (defer YAML support).

### 2026-01-26
- **Decision**: Use TOML for all configuration (profiles, tool groups, templates); no YAML support initially.
- **Rationale**: TOML is in Python stdlib (tomllib); simpler tooling; aligns with pyproject.toml conventions.
- **Trade-offs**: YAML is more familiar to some users; may add later if demanded.

### 2026-01-26
- **Decision**: Defer hot-reload for profiles/tools; manual restart required for config changes.
- **Rationale**: Simplicity; watchfiles adds dependency.
- **Trade-offs**: Less convenient for rapid iteration; revisit when UI profile editor matures.

### 2026-01-25
- **Decision**: Use a uv workspace with `agent_toolkit` (library) and `frontend/backend` (FastAPI backend).
- **Rationale**: Enables reuse, isolates backend from core runtime logic, and supports future extraction.
- **Trade-offs**: Shared Python version across members; requires workspace-aware dependency management.

### 2026-01-25
- **Decision**: Add a dedicated `frontend/` pnpm workspace with a Vite-based web app and reusable packages.
- **Rationale**: Deliver a browser-first Assistant UI playground while keeping web tooling isolated from the Python workspace.
- **Trade-offs**: Dual toolchains (uv + pnpm) and additional Docker compose workflows to manage.

---

## Anti-Patterns to Avoid

- **Monolithic agents** with broad tool access (violates 12-Factor #10).
- **Context stuffing** without compression or summarization.
- **Hardcoded tool lists** in code instead of config.
- **Tighter control instead of safer autonomy**—add guardrails, not micromanagement.
- **Demo-optimized patterns** that don't scale to real workloads.

---

## References

- [Vision](../vision.md)
- [Building Blocks](../building-blocks.md)
- [Deep Research Protocol](../prompts/deep-research-refactor-prompt.md)
