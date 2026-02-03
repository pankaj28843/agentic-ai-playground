# Inspiration → Playground Pattern Map

Purpose: Map external inspiration patterns to the Agentic AI Playground (Strands SDK + Python + assistant-ui), with translation strategies and target modules.

| Pattern | Intent | Translation Strategy | Target Module(s) | Notes |
| --- | --- | --- | --- | --- |
| Event-streamed agent loop | Deterministic UI updates | Unified event schema + adapter to Strands events | `packages/agent_toolkit/events.py`, backend stream | Enables trace panel parity |
| Session JSONL tree | Branching + replayable history | SessionManager + JSONL store | `packages/agent_toolkit/session/` | Supports branch navigation |
| Compaction + branch summaries | Context hygiene | Summarizer pipeline + structured summaries | `packages/agent_toolkit/compaction/` | Hooks for customization |
| Skills / prompts | Progressive disclosure | Resource loader + slash commands | `packages/agent_toolkit/resources/`, web UI | Load on demand |
| Extensions + hooks | Custom workflows | Extension API with hooks | `packages/agent_toolkit/extensions/` | Safe error isolation |
| Plan mode | Read-only planning | Profile + plan-mode hook | `packages/agent_toolkit/plan_mode.py` | No shell exposure |
| Subagents | Context isolation | Subagent tool + profiles | `packages/agent_toolkit/subagents/` | Chain/parallel |
| Tool output truncation | Context control | Shared truncation utilities | `packages/agent_toolkit/tools/truncation.py` | UI/LLM split |
| Observability-first UX | Traceability | Trace panel parity + snapshots | frontend trace panel | Expose tool activity |
