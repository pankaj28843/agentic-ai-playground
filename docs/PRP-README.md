## What is PRP?

**Product Requirement Prompt (PRP)**

### In short

A PRP is **PRD + curated codebase intelligence + agent/runbook** — the minimum viable packet an AI needs to plausibly ship production-ready code on the first pass.

Product Requirement Prompt (PRP) is a structured prompt methodology first established in summer 2024 with context engineering at heart. A PRP supplies an AI coding agent with everything it needs to deliver a vertical slice of working software — no more, no less.

### How PRP differs from a traditional PRD

A traditional PRD clarifies what the product must do and why customers need it, but deliberately avoids how it will be built.

A PRP keeps the goal and justification sections of a PRD yet adds three AI-critical layers:

- **Context**: precise file paths and content, library versions and library context, code snippets examples. LLMs generate higher-quality code when given direct, in-prompt references instead of broad descriptions.
- **Codebase intelligence**: project-specific patterns, gotchas, and anti-patterns (e.g., DDD aggregate conventions).
- **Agent/runbook**: phased implementation steps + validation commands and stop/go gates.

---

## Mandatory operating contract for every PRP plan

Every PRP plan **MUST** include an explicit operating contract so that when a user says **"Do next steps"** the agent knows exactly what "next" means without additional prompting.

### "Do next steps" protocol (required)

In any ongoing chat where the plan is selected/active:

1. **Always re-check the plan file first**
   If there is *any* uncertainty about what "next" means, re-open the plan and consult:
   - the **Implementation Blueprint** checklists
   - the **What else remains?** section (required — see below)

2. **Interpret "next steps" deterministically**
   - "Next steps" = the **earliest/nearest incomplete checklist items** in the current phase.
   - Do **not** skip phases unless the plan explicitly allows parallelism.
   - If blocked, stop and **record the blocker in the plan** (see "Plan watchers" below), then proceed with the next unblocked item if one exists.

3. **After finishing work, update plan watchers**
   - Update the **Status Snapshot** (timestamped).
   - Update the checklist progress.
   - Update **What else remains?** so it remains the single source of truth.

4. **If everything is implemented**
   - **Redeploy** and run the **full validation loop** (end-to-end), not just unit tests.
   - Then write a final Status Snapshot that includes the redeploy + full validation evidence.

5. **If not everything is implemented**
   - Focus immediately on implementing what remains.
   - Stop when all plan items are done, or you hit a new blocker and have recorded it.

### Plan watchers requirement (required)

Each plan must include a status section designed for "plan watchers" (people skimming progress):

- A **Status Snapshot (YYYY-MM-DD)** block near the top (newest first)
- A **Blockers / Risks** area that stays current
- A **Status cadence** rule (when the agent must post/update snapshots)
- A **What else remains?** section that is kept current

> If the plan is never used, it still must contain this contract so the *first use* is unambiguous.

### CI discipline (required)

- Always run the full CI-equivalent checks locally before pushing.
- If CI requires multiple toolchains (lint, tests, e2e), run them all and document results.
- After pushing, use `gh pr checks --watch --interval 10` to wait for CI completion before saying work is done.
- If any check fails locally or remotely, fix before reporting completion.

---

## File naming and location

**All PRP plans live in `~/prp-plans/agentic-ai-playground/`** (never checked in to version control).

Use timestamped filenames:
- Format: `<ISO-8601-timestamp>-<short-description>.md`
- Generate timestamp: `date -u +"%Y-%m-%dT%H:%M:%SZ"`
- Examples:
  - `2026-01-07T22-47-21Z-coverage-95-ci-enforcement-plan.md`
  - `2026-01-06T23:32:03Z-docs-mcp-server-crawl-dedup.md`

---

## Creating effective PRP plans

### When to create a PRP plan

Create a detailed PRP plan for **non-trivial** tasks that require:
- Multiple actions across several files or modules
- Complex logic that needs careful analysis before implementation
- Refactoring that impacts existing functionality
- Integration between multiple systems or services
- Testing strategy that spans multiple layers (unit, integration, e2e)

Skip PRP planning for trivial tasks like:
- Single file edits or bug fixes
- Adding simple fields to models
- Basic configuration changes
- Straightforward documentation updates

---

## Required PRP plan sections

A comprehensive PRP plan should include:

1. **Goal / Why / Success Metrics**
   - What: clear, specific description of what needs to be built/changed
   - Why: business justification and value proposition
   - Success criteria: measurable outcomes / acceptance criteria

2. **Current state**
   - Existing code review: what exists today + where
   - Dependencies: what modules/services are involved
   - Constraints: technical limits or requirements
   - Risks: what could go wrong and mitigation strategies
   - References to specific files/lines (preferred)

3. **Implementation blueprint**
   - Phased approach: sequential phases (with optional explicit parallelism)
   - File-by-file changes: specific files and what changes
   - Data structures: models, schema, migrations if needed
   - API changes: endpoints + contracts
   - Testing strategy: what to test and where
   - **Checklist format required**: each step must be a checkbox so "next" is computable.

4. **Context & anti-patterns**
   - Known project gotchas and patterns to follow/avoid
   - Code quality standards and tooling requirements
   - Integration points with existing systems

5. **Validation loop**
   - Level 1: syntax/imports
   - Level 2: unit tests
   - Level 3: integration tests
   - Level 4: docker deploy + end-to-end validation

6. **Open questions & risks**
   - Blockers, missing context, required approvals
   - "If X happens, do Y" mitigations

7. **Plan watchers**
   - Status snapshot(s)
   - Blockers / risks
   - Status cadence
   - **What else remains?** (single source of truth for next steps)

---

## Anti-patterns in PRP planning

Avoid these planning mistakes:

### Over-planning trivial tasks
- Don't create 50-line PRPs for single-method changes
- Skip formal planning for obvious implementations
- Use judgment — if it's a 5-minute fix, just do it

### Under-analyzing complex changes
- Don't start coding complex refactors without understanding current state
- Always analyze existing patterns before introducing new ones
- Map out dependencies and integration points first

### Generic implementation blueprints
- Avoid vague steps like "update the models" or "add tests"
- Include specific file paths, method names, and code patterns
- Reference existing code examples and conventions

### Missing anti-pattern analysis
- Always include project-specific patterns to follow/avoid
- Document quality standards and tooling requirements
- Include validation steps that catch common mistakes

### Inadequate context gathering
- Don't assume — search existing codebase for similar patterns
- Include related code snippets and integration examples
- Document dependencies and potential side effects
