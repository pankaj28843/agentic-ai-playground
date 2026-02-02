# Deep Research & Refactor Protocol

> **Goal**: Keep the playground following best practices with easy-to-maintain, plug-and-play code.

This protocol guides deep research and refactoring cycles. Use TechDocs as a toolbox—not to summarize, but to anchor decisions in proven patterns.

---

## Alignment

Before any refactor, ensure alignment with:

- [Vision](../vision.md) — Core philosophy and success criteria
- [Architecture Decisions](../architecture/decisions.md) — Trade-offs and guiding principles
- [Building Blocks](../building-blocks.md) — Tool registry, profiles, and factory APIs

---

## Agent-Native Mindset

Adopt these principles when evaluating or proposing changes:

| Principle | Implication |
|-----------|-------------|
| **Emergent behavior > rigid workflows** | Don't over-prescribe; let agents discover solutions. |
| **Rich feedback loops > perfect prompts** | Invest in observability, error compaction, iteration. |
| **Context is curated and fragile** | Compartmentalize; use sub-agents; protect context hygiene. |
| **Cost is acceptable if value compounds** | Optimize for leverage, not token counts. |
| **Long-running, async, multi-agent** | Design for 10–30+ minute tasks, not just quick demos. |
| **Clean-slate iteration > backward compatibility** | The playground can reset state (including `./.data`) to stay lean and forward-looking. |

**Challenge any design that:**
- Centralizes control unnecessarily
- Stuffs context aggressively without compression
- Optimizes for demo performance over real workloads
- Avoids autonomy "for safety" instead of building safer autonomy

---

## System Tools

- **TechDocs MCP**: Primary source for patterns, official docs, and best practices.
- **PRP Plans**: Create in `~/prp-plans/agentic-ai-playground/` with timestamped filenames.

```bash
# Generate timestamp for plan filename
date -u +"%Y-%m-%dT%H-%M-%SZ"
# Example: ~/prp-plans/agentic-ai-playground/2026-01-28T07-30-00Z-streaming-refactor.md
```

---

## Planning Discipline (CRITICAL)

> **⚠️ Hard-Learned Lesson**: Planning files scattered across the repo or without timestamps
> create chaos. When debugging a tough issue, you need to reconstruct what happened and when.
> Timestamped plans in a central location make this possible.

### Rules for Planning

1. **All plans in ONE folder**: `~/prp-plans/agentic-ai-playground/`
   - Never create plan files in the repo itself
   - Never create ad-hoc notes without timestamps
   - This folder is your project's memory

2. **Always use timestamps**: `<ISO-8601-timestamp>-<short-description>.md`
   ```bash
   # Generate timestamp
   date -u +"%Y-%m-%dT%H-%M-%SZ"
   # Creates: 2026-01-28T16-00-00Z-tool-execution-fix.md
   ```

3. **Plans are sequential history**: When you read `~/prp-plans/agentic-ai-playground/`:
   - Files sort chronologically by name
   - You can trace what happened and in what order
   - Each plan captures the state at that moment

4. **Update plans as you work**: Check off completed items, add new discoveries
   - Plans are living documents during implementation
   - Final state becomes the historical record

### Why This Matters

During a recent debugging session, we traced a bug through multiple components:
- ResilientMCPClient → ToolProvider interface → Agent prompts → Streaming format

Without timestamped plans, we would have lost track of:
- What we tried and why it failed
- The order of discoveries
- The root cause analysis

---

## Protocol

### 1. Research & Plan (10 iterations minimum)

Each iteration:
1. **Query TechDocs** with fresh perspective—target specific patterns:
   - Agentic Patterns (Oracle/Worker, progressive disclosure, skill libraries)
   - 12-Factor Agents (small agents, stateless reducers, context ownership)
   - Clean Code / Clean Architecture
2. **Anchor claims to patterns**: Reference by name; prefer pattern combinations.
3. **Think in systems**: Context → orchestration → feedback → learning → UX.
4. **Highlight second-order effects** and failure modes.
5. **Refine the plan**: Identify impacted modules, test strategy, risks, success criteria.

### 2. Pattern-Based Analysis

Before implementing, perform:

#### Pattern Coverage Audit
- Which pattern categories are we **underusing**?
- Which are we **overusing** or **misusing**?
- What **missing primitives** limit agent autonomy or scale?

#### Architectural Stress Test
Evaluate how the solution behaves under:
- Long-running tasks (10–30+ minutes)
- Large codebases or datasets
- Partial failures (tool errors, flaky CI, bad context)

Propose **specific pattern-based mitigations**.

#### Human Role Definition
- What should humans **decide**?
- What should agents **own**?
- Propose **guardrails and nudges**, not tighter control.

### 3. Implementation (20 cycles max)

1. Work on a dedicated feature branch off `origin/main`.
2. Implement in **small, composable changes**—prefer refactors over rewrites.
3. Run validation loop after each major change.
4. Push and maintain PR as you go.

### 4. Commit & PR Hygiene

**Commit messages**: Describe *what* changed, not *why you researched it*.
```
# Good
refactor: extract tool resolution into ToolResolver class

# Bad
refactor: apply progressive disclosure pattern per TechDocs research
```

**PR description**: Focus on the change and its trade-offs.
```
# Good
Extracts tool resolution logic into a dedicated ToolResolver class.
- Enables lazy tool loading (progressive disclosure pattern)
- Reduces config loader complexity by ~40 lines
- Trade-off: Adds one more module to maintain

# Bad
After 10 iterations of TechDocs research on progressive disclosure...
```

---

## Workflow Rules

### Test Fixtures
- **Do not modify existing test fixtures** to make failing tests pass.
- If coverage is missing, **add new fixtures**—never edit existing ones.

### Work Style
- Work in **deep cycles**: research → plan → implement → validate.
- Every change on a **fresh branch off `origin/main`**.
- Use **GitHub CLI** to create/maintain PR.

### Validation Loop

Before every push:
```bash
# Level 1: Python lint
uv run ruff check . --fix && uv run ruff format .

# Level 2: Python tests
uv run pytest packages/ -x -q

# Level 3: Frontend lint
pnpm -C frontend lint

# Level 4: Frontend build
pnpm -C frontend build
```

### E2E Testing (CRITICAL — Run After Every Significant Change)

> **⚠️ Lesson Learned**: Skipping E2E tests leads to cascading bugs. In one debugging session,
> we discovered tool calls weren't executing (just being described in text) because
> `ResilientMCPClient` didn't implement Strands' `ToolProvider` interface. This was only
> caught by running E2E tests that verified actual tool execution.

**Always run BOTH types of E2E tests** — they catch different issues:
- **Playwright tests** catch UI regressions, trace panel bugs, visual issues
- **Python API tests** catch streaming format issues, tool execution failures, protocol bugs

#### Step 1: Clean Docker Restart

Before running E2E tests, ensure a clean deployment:

```bash
# Full restart with log streaming (RECOMMENDED)
uv run python scripts/restart_frontend_compose.py

# What it does:
# 1. Stops existing containers gracefully
# 2. Rebuilds images with --no-cache
# 3. Starts fresh containers
# 4. Streams logs to ./logs/frontend/<date>/
# 5. Saves pre-restart log snapshots
```

**If containers are stuck or behaving oddly:**
```bash
# Nuclear option: kill everything and restart
docker compose -f frontend/docker-compose.yml down -v
uv run python scripts/restart_frontend_compose.py
```

#### Step 2: Run Playwright E2E Tests

```bash
# Run all E2E specs (REQUIRED before pushing UI changes)
pnpm -C frontend exec playwright test --reporter=list

# Run specific test file
pnpm -C frontend exec playwright test tool-calls.spec.ts

# Run with UI for debugging failures
pnpm -C frontend exec playwright test --ui
```

**E2E Test Files** (`frontend/apps/web/tests/e2e/`):
| File | What It Tests |
|------|---------------|
| `tool-calls.spec.ts` | **Tool execution** — verifies TechDocs tools actually run (not just described) |
| `chat.spec.ts` | Chat UI, send messages, response rendering |
| `modes.spec.ts` | Mode switching (single/graph/swarm) |
| `api.spec.ts` | API health and profile loading |

#### Step 3: Run Python API E2E Tests

```bash
# Consolidated API E2E suite (REQUIRED before pushing agent changes)
source .env && uv run python scripts/e2e_tests.py
```

**What Python E2E tests catch:**
- Tool-call content types missing from stream
- Models describing tools instead of calling them (broken ToolProvider)
- Agent attribution missing in swarm/graph modes
- Fake URLs in responses (indicates hallucination, not real tool use)

#### Step 4: TUI E2E Validation (Optional, Costs Money)

```bash
# Quick connectivity check
source .env && uv run python scripts/debug_tui_runtime.py --preflight

# Full agent loop test
source .env && uv run python scripts/debug_tui_runtime.py --prompt "list tenants (first 5)"
```

### When to Add New E2E Tests

**Add E2E tests when:**
- Adding new agent capabilities (tool providers, modes, profiles)
- Changing streaming format or content types
- Modifying trace panel or UI interactions
- Fixing bugs that weren't caught by existing tests

**E2E test pattern:**
```typescript
// Verify behavior, not implementation details
test("swarm mode executes tools with agent attribution", async ({ page }) => {
  // 1. Set up state
  await page.getByRole("combobox", { name: "Mode" }).selectOption("swarm");

  // 2. Trigger action
  await input.fill("Search TechDocs for FastAPI docs.");
  await page.getByRole("button", { name: "Send" }).click();

  // 3. Verify observable outcome
  const tracePanel = page.locator('[role="complementary"][aria-label="Agent trace"]');
  const toolCalls = tracePanel.locator("button").filter({ hasText: /\[.*\].*TechDocs_/ });
  expect(await toolCalls.count()).toBeGreaterThanOrEqual(1);
});
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Why It's Bad |
|--------------|--------------|
| Monolithic agents | Context pollution; harder to test; violates 12-Factor #10. |
| Hardcoded tool lists | Inflexible; requires code changes for config changes. |
| Context stuffing | Degrades LLM performance; loses focus on long tasks. |
| Demo-optimized code | Doesn't scale; hides failure modes. |
| Tighter control for safety | Micromanagement; prefer guardrails and escalation. |
| **Skipping E2E tests** | Bugs compound silently; tool execution issues go unnoticed. |
| **Plans outside central folder** | History lost; debugging becomes archaeological dig. |
| **Untimestamped plans** | Can't reconstruct sequence of events; decisions float in void. |

---

## Debugging Lessons (Case Studies)

### Case Study: Tool Calls Not Executing

**Symptom**: Swarm and graph modes showed "Thinking" in trace panel but no actual tool calls.
The LLM was outputting text like `TechDocs_list_tenants() → [...]` instead of calling tools.

**Root Cause**: `ResilientMCPClient` wrapper didn't implement Strands SDK's `ToolProvider` interface.
The SDK logged "unrecognized tool specification" and silently ignored the tool provider.

**How We Found It**:
1. Playwright E2E tests showed trace panel missing `tool-call` type items
2. Python API tests detected fake tool syntax in response text
3. Direct testing with `strands.Agent` showed the warning in logs
4. Traced through Strands source to find `ToolProvider` ABC requirements

**Fix**: Implement `add_consumer()`, `remove_consumer()`, and async `load_tools()` methods.

**Lesson**: E2E tests that verify *behavior* (tools actually execute) catch issues that unit tests miss.

### Case Study: Prompts Causing Role-Play

**Symptom**: Even with correct ToolProvider, LLM was "role-playing" tool calls in text.

**Root Cause**: Agent prompts contained code block examples showing tool call syntax:
```
# BAD - LLM emulates this format
TechDocs_list_tenants() → [{"codename": "django", ...}]
```

**Fix**: Rewrite prompts to say "CALL tools directly - do NOT describe them in text."
Remove all code block examples that showed tool call/response format.

**Lesson**: LLMs are pattern matchers. If you show a format, they'll output that format.

---

## Output Format for Analysis

When performing deep analysis, structure output as:

```
## Executive Diagnosis
(High-level assessment in 5–7 bullets)

## Pattern-Level Gaps
- Gap → Impact → Relevant Patterns

## Top Improvement Proposals
### Proposal A
- Patterns used:
- Description:
- Why this works:
- Risks & trade-offs:

## Anti-Patterns Detected
(Explicit warnings based on TechDocs lessons)

## Highest-Leverage Change
(The single most impactful refactor if we did nothing else)
```

---

## Priority Guidelines

- Prioritize **maintainability and composability** over feature velocity.
- Resolve merge conflicts first, then merge, then continue.
- Use **TechDocs aggressively**—it's free and fast.
- **Ask**: "Does this make the agent more capable without human micromanagement?"

---

## References

- [Vision](../vision.md)
- [Architecture Decisions](../architecture/decisions.md)
- [Building Blocks](../building-blocks.md)
- [Operations](../operations.md)
- [PRP Methodology](../PRP-README.md)
- [PRP Template](../PRP-PLAN-TEMPLATE.md)
