# <PRP Title>

> **File location**: Save this plan to `~/prp-plans/agentic-ai-playground/<timestamp>-<short-name>.md`
> Generate timestamp with: `date -u +"%Y-%m-%dT%H:%M:%SZ"`
> Example: `~/prp-plans/agentic-ai-playground/2026-01-07T22-47-21Z-coverage-95-ci-enforcement-plan.md`

## Plan Operator Contract ("Do next steps")

When the user says **"Do next steps"** (or "yes do the next steps"):
- Always open/re-check **this plan file** first.
- "Next steps" = the **next incomplete checkbox items** in **Implementation Blueprint**, starting from the earliest incomplete phase.
- If unsure what to do next, **recheck `## What else remains?`** and resume from the topmost unfinished item.
- After you finish each chunk of work, **update this plan**:
  - Add/refresh a **Status Snapshot** entry (newest first)
  - Update checkboxes
  - Update **Blockers / Risks** and **What else remains?**
- If all items are complete:
  - Redeploy
  - Run the full validation loop (end-to-end)
  - Record results in Status Snapshot
- If items remain incomplete:
  - Implement what remains immediately
  - Stop when all items are done or when a new blocker is recorded.

## CI Discipline
- Always run the full CI-equivalent checks locally before pushing.
- If CI requires multiple toolchains (lint, tests, e2e), run them all and document results.
- After pushing, use `gh pr checks --watch --interval 10` to wait for CI completion before saying work is done.
- If any check fails locally or remotely, fix before reporting completion.

## Status Snapshot (<YYYY-MM-DD>)
- (Most recent updates first; include commands run + outcomes + key metrics + blockers.)
- Example bullets:
  - ✅ …
  - ⚙️ …
  - 📊 …
  - ⛔ Blocker: …

## Goal / Why / Success Metrics
- **Goal**:
- **Why**:
- **Success metrics**:
  - [ ] Metric 1
  - [ ] Metric 2

## Current State
- Existing behavior:
- Key files:
- Dependencies:
- Constraints:
- Risks:

## Implementation Blueprint (checklist required)

### Phase 0 — Recon / alignment
- [ ] Step 0.1 — …
  - Files:
  - Notes:
  - Validation:

### Phase 1 — Core implementation
- [ ] Step 1.1 — …
- [ ] Step 1.2 — …

### Phase 2 — Tests & hardening
- [ ] Step 2.1 — …
- [ ] Step 2.2 — …

### Phase 3 — Deploy & end-to-end validation
- [ ] Step 3.1 — Redeploy
- [ ] Step 3.2 — Full validation loop
- [ ] Step 3.3 — Final status snapshot + handoff notes

## Context & Anti-Patterns
- Patterns to follow:
- Anti-patterns to avoid:
- Gotchas:

## Validation Loop
- Level 1:
- Level 2:
- Level 3:
- Level 4:

## Open Questions & Risks
- Q1:
- Risk 1:
- Mitigation:

## Plan Watchers
- **Status cadence**: update Status Snapshot after each phase completion or whenever a new blocker appears.
- **Current blockers**:
  - None / …
- **Decision log** (optional):
  - …

## What else remains?
> Keep this list in sync with the checkboxes above. This is the single source of truth for "next steps".

- [ ] <Top unfinished item>
- [ ] …
- [ ] …
