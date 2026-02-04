# Inspiration Dossier

Purpose: Capture transferable patterns from external reference implementations and agent research, and map them to the Agentic AI Playground (Python + Strands SDK + assistant-ui).

## Sources Reviewed
- External open-source agents and public engineering writeups
- Internal prototyping notes

## Core Patterns Worth Porting

### 1) Event-Streamed Agent Loop
- **Inspiration**: Agents emit a strict, observable event sequence (agent_start → turn_start → message_update → tool_execution_* → turn_end → agent_end).
- **Why it matters**: Enables deterministic UI updates, trace panels, and observability without hidden state.
- **Translation**: Define a canonical `AgentEvent` in `agent_toolkit`, add Strands adapter, and ensure frontend renders full event stream.

### 2) Session Tree with JSONL
- **Inspiration**: Sessions stored as JSONL with tree branching, labels, compaction summaries, and branch summaries.
- **Why it matters**: Enables branch navigation, fork/branch workflows, and reproducible context.
- **Translation**: Add SessionManager for JSONL tree persistence + branch navigation in web UI.

### 3) Compaction + Branch Summaries
- **Inspiration**: Structured summaries (Goal/Constraints/Progress/Next Steps/Files) to prevent context overload.
- **Why it matters**: Context hygiene for long-running, multi-turn tasks.
- **Translation**: Add compaction pipeline with split-turn handling and extension hooks for customization.

### 4) Progressive Disclosure (Skills / Prompts / Context Files)
- **Inspiration**: Skills (SKILL.md) and prompt templates loaded only when invoked; context files (AGENTS.md) discovered by scope.
- **Why it matters**: Protects context window; allows modular capability expansion.
- **Translation**: Implement ResourceLoader with global + project scope, collisions diagnostics, and slash commands in UI.

### 5) Extensions + Hook System
- **Inspiration**: Extensions register tools, commands, and lifecycle hooks; safe error handling; UI widgets.
- **Why it matters**: Keeps core minimal, allows user-specific workflows.
- **Translation**: Python extension API with event hooks and tool registration, including strict error isolation.

### 6) Plan Mode (Read-Only) as Extension
- **Inspiration**: Plan mode restricts tools, extracts plan steps, uses `[DONE:n]` markers.
- **Why it matters**: Safe exploration and predictable planning.
- **Translation**: Implement as extension/profile with UI toggle; add tests to ensure no write operations.

### 7) Subagents via Tool
- **Inspiration**: Subagent extension spawns isolated agents, supports chain/parallel, streams progress.
- **Why it matters**: Context isolation and parallel discovery.
- **Translation**: Subagent tool in toolkit + profiles for scout/planner/worker; UI attribution.

### 8) Tool Output Truncation + Split Results
- **Inspiration**: Truncation helpers + split tool output for LLM vs UI.
- **Why it matters**: Prevents context blowups; enables better UI rendering.
- **Translation**: Shared truncation utilities + tool result schema with `llm_content` and `ui_content`.

### 9) Multi-Provider Abstraction + Context Handoff
- **Inspiration**: Unified provider model registry with cross-provider handoff.
- **Why it matters**: Enables model agility.
- **Translation**: Align Strands provider registry; add optional handoff helpers.

### 10) Observability-First UX
- **Inspiration**: Tool calls, prompt injections, and summaries are visible to the user.
- **Why it matters**: Debuggability and trust.
- **Translation**: Trace panel parity + session export pipeline.

## Design Tenets (Key Takeaways)
- Minimal system prompt and small default toolset for predictability.
- Avoid hidden context injection; surface all prompt additions and tool activity in UI.
- Keep features out of core unless essential; workflows live in extensions.
- Separate LLM output from UI representation for tool results.
- Favor low-flicker UI via retained-mode/diff rendering.

## Divergences for Playground
- **Web-first UI**: The playground is web-first; patterns translate to React UI behaviors.
- **Chat-first UX**: This is a web-based chat bot and not a coding agent IDE; user interaction stays in-chat.
- **No shell execution**: The UI does not expose shell execution on behalf of users.
- **No backward compatibility**: Playground can break state; prioritize best UX and maintainability.

## Actionable Recommendations
1. Implement unified event schema + adapter to Strands events.
2. Add JSONL session tree with branching, labels, and export.
3. Implement compaction with structured summaries + extension hooks.
4. Build ResourceLoader for skills/prompts/context files with progressive disclosure.
5. Build extension runtime for tools/commands/hook events.
6. Add plan-mode extension (read-only tools only).
7. Add subagent tool (chain + parallel) with UI attribution.
8. Introduce truncation utilities + split tool results for UI/LLM.
9. Add lightweight UI levers for mode/tools/skills.
10. Expand tests: near-100% unit coverage for touched files; E2E for tool visibility/streaming.
