# Pi-Mono Inspiration Dossier

Purpose: Capture transferable patterns from pi-mono (pi-ai, pi-agent-core, pi-coding-agent) and the pi coding agent blog, and map them to the Agentic AI Playground (Python + Strands SDK + assistant-ui).

## Sources Reviewed
- pi-mono repo (local clone)
- Blog: “What I learned building an opinionated and minimal coding agent” (2025-11-30)

## Core Patterns Worth Porting

### 1) Event-Streamed Agent Loop
- **Pi-mono**: Agent emits a strict, observable event sequence (agent_start → turn_start → message_update → tool_execution_* → turn_end → agent_end).
- **Why it matters**: Enables deterministic UI updates, trace panels, and observability without hidden state.
- **Translation**: Define a canonical `AgentEvent` in `agent_toolkit`, add Strands adapter, and ensure frontend renders full event stream.

### 2) Session Tree with JSONL
- **Pi-mono**: Sessions stored as JSONL with tree branching, labels, compaction summaries, and branch summaries.
- **Why it matters**: Enables “/tree” navigation, fork/branch workflows, and reproducible context.
- **Translation**: Add SessionManager for JSONL tree persistence + branch navigation in web UI.

### 3) Compaction + Branch Summaries
- **Pi-mono**: Structured summaries (Goal/Constraints/Progress/Next Steps/Files) to prevent context overload.
- **Why it matters**: Context hygiene for long-running, multi-turn tasks.
- **Translation**: Add compaction pipeline with split-turn handling and extension hooks for customization.

### 4) Progressive Disclosure (Skills / Prompts / Context Files)
- **Pi-mono**: Skills (SKILL.md) and prompt templates only loaded when invoked; context files (AGENTS.md) discovered by scope.
- **Why it matters**: Protects context window; allows modular capability expansion.
- **Translation**: Implement ResourceLoader with global + project scope, collisions diagnostics, and slash commands in UI.

### 5) Extensions + Hook System
- **Pi-mono**: Extensions register tools, commands, and lifecycle hooks; safe error handling; UI widgets.
- **Why it matters**: Keeps core minimal, allows user-specific workflows.
- **Translation**: Python extension API with event hooks and tool registration, including strict error isolation.

### 6) Plan Mode (Read-Only) as Extension
- **Pi-mono**: Plan mode restricts tools, allowlists bash, extracts plan steps, uses `[DONE:n]` markers.
- **Why it matters**: Safe exploration and predictable planning.
- **Translation**: Implement as extension/profile with UI toggle; add tests to ensure no write operations.

### 7) Subagents via Tool
- **Pi-mono**: Subagent extension spawns isolated agents, supports chain/parallel, streams progress.
- **Why it matters**: Context isolation and parallel discovery.
- **Translation**: Subagent tool in toolkit + profiles for scout/planner/worker; UI attribution.

### 8) Tool Output Truncation + Split Results
- **Pi-mono**: Truncation helpers + split tool output for LLM vs UI.
- **Why it matters**: Prevents context blowups; enables better UI rendering.
- **Translation**: Shared truncation utilities + tool result schema with `llm_content` and `ui_content`.

### 9) Multi-Provider Abstraction + Context Handoff
- **Pi-mono**: Unified provider model registry with cross-provider handoff.
- **Why it matters**: Enables model agility.
- **Translation**: Align Strands provider registry; add optional handoff helpers.

### 10) Observability-First UX
- **Pi-mono**: Tool calls, prompt injections, and summaries are visible to the user.
- **Why it matters**: Debuggability and trust.
- **Translation**: Trace panel parity + session export pipeline.

## Blog-Derived Design Tenets (Key Takeaways)
- Minimal system prompt and small default toolset for predictability.
- Avoid hidden context injection; surface all prompt additions and tool activity in UI.
- Keep features out of core unless essential; workflows live in extensions.
- Multi-provider support and context handoff are first-class.
- Separate LLM output from UI representation for tool results.
- Favor low-flicker UI via retained-mode/diff rendering (inspiration for React UI).

## Divergences for Playground
- **MCP**: pi-mono avoids MCP; the playground uses TechDocs MCP as a primary grounding source.
- **Web-first UI**: pi-mono is TUI-first; playground is web-first, so UI mapping is a translation.
- **No backward compatibility**: playground can break state; prioritize best UX and maintainability.

## Actionable Recommendations
1. Implement unified event schema + adapter to Strands events.
2. Add JSONL session tree with branching, labels, and export.
3. Implement compaction with structured summaries + extension hooks.
4. Build ResourceLoader for skills/prompts/context files with progressive disclosure.
5. Build extension runtime for tools/commands/hook events.
6. Add plan-mode extension (read-only tools + allowlist bash).
7. Add subagent tool (chain + parallel) with UI attribution.
8. Introduce truncation utilities + split tool results for UI/LLM.
9. Add lightweight UI levers for mode/tools/skills.
10. Expand tests: near-100% unit coverage for touched files; E2E for tool visibility/streaming.
