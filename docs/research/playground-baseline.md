# Playground Baseline (Current Architecture)

Purpose: Capture the current runtime, streaming, session, and UI behavior for gap analysis against pi-mono patterns.

## Runtime Core
- **AgentRuntime**: Orchestrates agent creation + execution strategies (single, swarm, graph). Uses Strands agents and telemetry (see `packages/agent_toolkit/src/agent_toolkit/runtime.py`).
- **Execution strategies**: `SingleAgentStrategy`, `SwarmStrategy`, `GraphStrategy` and run-mode resolvers via config.
- **AgentFactory**: Builds Strands agents from TOML-defined profiles and tool registry.

## Streaming & Events
- **Raw Strands events** are consumed in `stream_utils` with `OutputAccumulator` and metrics extraction.
- **StreamChunk** exists as a normalized abstraction but is not the primary runtime path.
- **Backend stream**: `assistant_web_backend/services/streaming.py` accumulates tool calls, reasoning, agent events and returns assistant-ui content parts.
- **Trace panel**: Web UI uses `TraceContext` and `TracePanel` to show tool calls and agent events.

## Session Management
- Uses Strands session adapters via `build_memory_session_manager`:
  - `FileSessionManager` (default)
  - `AgentCoreMemorySessionManager` (optional)
- Session storage is a directory-based store under `.data/sessions` (configurable).
- No JSONL tree session format or branch navigation UI exists yet.

## Compaction / Context Management
- Uses Strands `SlidingWindowConversationManager` or `SummarizingConversationManager` (configurable).
- Summaries are internal to Strands and do not currently expose structured compaction summaries or branch summaries.

## Tool Registry & Hooks
- Tool registry exists with metadata and progressive detail levels.
- Tool adapters for Strands tools are supported (registry resolves `strands:` prefix).
- Hooks include tool approval, telemetry, and TechDocs workflow enforcement.

## Web UI
- Primary UI uses assistant-ui components with a trace panel.
- No explicit UI levers for plan mode, subagents, skills/prompts toggling.
- Trace panel already supports tool events, agent events, and Phoenix metadata.

## Backend API
- FastAPI backend provides streaming chat endpoint `/api/chat/run`.
- Stream converts messages into Strands format and returns rich content parts.
- Tool results are converted to text; no split UI/LLM output schema.

## Gaps vs pi-mono (High-Level)
- No session tree (branching, labels, compaction summaries).
- No explicit extension system with lifecycle hooks and UI widgets.
- No skills/prompt templates with progressive disclosure in UI.
- No plan mode or subagent orchestration as a tool.
- No structured compaction summary or branch summaries.
- Tool output truncation exists as a setting but is not standardized per-tool.

## Notes
- Config is TOML-driven (agents, tools, graphs, swarms) with environment-driven settings.
- Web UI already has a trace panel but event schema alignment is incomplete.
