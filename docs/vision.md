# Agentic AI Playground Vision

## Mission

Build an evolving agent platform that makes it easy to design, test, and iterate on small, focused agents. The playground is a proving ground for agentic patterns—prioritizing **plug-and-play composability**, **emergent behavior over rigid workflows**, and **maintainable code** that follows production-grade best practices.

## Core Philosophy

### Agent-Native Mindset
- **Emergent behavior over rigid workflows**: Let agents discover solutions rather than prescribing every step.
- **Rich feedback loops beat perfect prompts**: Invest in observability, error compaction, and iterative refinement.
- **Context is curated and fragile**: Protect context hygiene; use sub-agents and compartmentalization.
- **Usage-based cost is acceptable if value compounds**: Optimize for leverage, not token counts.
- **Long-running, async, multi-agent work**: Design for tasks that span minutes, not seconds.

### Design Principles
- **Small, focused agents** (12-Factor Agents #10): Keep context windows manageable; 3–20 steps max per agent.
- **Composable building blocks**: Tools, profiles, and agents are declaratively configured and easily swapped.
- **Separation of concerns**: UI logic in apps, shared runtime logic in the toolkit library.
- **Clear module boundaries**: Reduce complexity through explicit interfaces, not fewer files.
- **Declarative configuration**: Models, tools, and profiles defined in TOML—no hardcoded magic.
- **Clean-slate velocity**: No backward compatibility promises; reset state (including `./.data`) whenever it prevents tech debt.

## Why This Repo Exists

1. **Pattern Laboratory**: Experiment with agentic patterns (Oracle/Worker, progressive disclosure, skill libraries) in a safe sandbox.
2. **Toolkit Development**: Build a reusable `agent_toolkit` library that can graduate to production.
3. **Best Practices Capture**: Document architectural decisions, failure modes, and trade-offs as the system evolves.
4. **Rapid Iteration**: No backward compatibility constraints—break things, learn, improve.

## Architecture Pillars

| Pillar | Description |
|--------|-------------|
| **Tool Registry** | Centralized catalog with metadata, progressive discovery, and capability-based filtering. |
| **Agent Profiles** | Declarative TOML definitions with inheritance, tool groups, and constraints. |
| **Agent Factory** | Creates Strands agents from profiles; supports agent-as-tool delegation. |
| **Multi-Agent Templates** | Graph and swarm orchestration patterns defined in config. |
| **TechDocs MCP** | Primary grounding source for agent answers; enables pattern-anchored reasoning. |

## Success Criteria

- Agents can be composed, extended, and swapped via configuration alone.
- The toolkit library is importable and testable in isolation.
- New patterns can be added without touching core runtime code.
- The codebase is readable, tested, and CI-enforced from day one.
- Developers can onboard by reading `docs/` without tribal knowledge.

## Related Documentation

- [Architecture Decisions](architecture/decisions.md) — Trade-offs and design rationale
- [Building Blocks](building-blocks.md) — Tool registry, profiles, and factory APIs
- [Operations](operations.md) — Debugging, exports, and CI expectations
- [Deep Research Protocol](prompts/deep-research-refactor-prompt.md) — Research and refactor workflow
