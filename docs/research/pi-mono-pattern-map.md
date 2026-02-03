# Pi-Mono → Playground Pattern Map

Purpose: Map pi-mono primitives to the Agentic AI Playground (Strands SDK + Python + assistant-ui), with translation strategies and target modules.

## Legend
- **Direct port**: re-implement concept in Python with minimal design change.
- **Strands-native**: use Strands SDK primitives, add adapters where needed.
- **New module**: implement custom module in agent_toolkit with no Strands analogue.

## Pattern Map

| Pi-Mono Pattern | Intent | Translation Strategy | Target Module(s) | Notes |
| --- | --- | --- | --- | --- |
| Event-streamed agent loop | Deterministic UI events | Strands-native + adapter | `agent_toolkit/events.py`, backend stream | Align event ordering with UI trace panel |
| Session JSONL tree | Branching + replay | New module | `agent_toolkit/session/` | Replace file sessions for tree support |
| Compaction summaries | Context hygiene | New module + hook | `agent_toolkit/compaction/` | Structured summaries + file ops |
| Branch summaries | Context handoff across branches | New module | `agent_toolkit/compaction/branch.py` | Inject summary entries |
| Skills (SKILL.md) | Progressive disclosure | New module | `agent_toolkit/skills/` | Global + project scope |
| Prompt templates | Slash expansion | New module | `agent_toolkit/prompts/` | UI expansion + args |
| Extensions + hooks | Customization / policy | New module | `agent_toolkit/extensions/` | Event hooks + commands + tools |
| Plan mode | Read-only exploration | Extension | `extensions/plan_mode.py` | Allowlisted bash + `[DONE:n]` |
| Subagents tool | Isolated context | New module | `agent_toolkit/subagents/` | Chain + parallel modes |
| Tool output truncation | Prevent context blowups | Strands-native + shared utils | `agent_toolkit/tools/utils.py` | Standard truncation helpers |
| Split tool results (LLM/UI) | Better rendering | New module | stream schema + UI | `llm_content` + `ui_content` |
| Model registry + handoff | Multi-provider usage | Strands-native | `agent_toolkit/providers/` | Add handoff helpers |
| Observability / trace | Debuggability | Strands-native + UI | trace panel + runtime metadata | Preserve tool/agent events |

## Dependencies & Ordering
1. Event schema (enables trace + tool visibility)
2. Session manager (storage backbone)
3. Compaction summaries (context hygiene)
4. Resource loader (skills/prompts/context files)
5. Extension runtime (customization backbone)
6. Plan mode + queueing (behavior)
7. Subagents tool (parallelism)
8. UI levers + session tree view

## Risks
- Strands event shape mismatch → requires adapter layer.
- Session tree migration → may invalidate existing sessions.
- Subagents tool → potential UX confusion without strong UI attribution.

## Validation Targets
- Unit test coverage near 100% for touched files.
- E2E: tool events visible, subagent attribution present, compaction summaries injected.
