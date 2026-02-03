# Compaction & Summaries

Compaction reduces long conversations into structured summaries to protect context windows.

## Core flow
1. **Prepare**: identify a safe boundary (prefer user turn) and gather file operations.
2. **Summarize**: produce a structured summary with goal, constraints, progress, decisions, and next steps.
3. **Persist**: write a `compaction` entry into the session tree, linking to the first kept entry.

## Structured summary format
Summaries are tagged so the UI and downstream agents can parse reliably:
- `<goal>` / `<constraints>` / `<done>` / `<in-progress>` / `<blocked>` / `<decisions>` / `<next-steps>`
- `<read-files>` / `<modified-files>`

## Hooks
Extensions can intercept compaction:
- `before_compact` can override the summary or change the keep boundary.
- `after_compact` can add telemetry or custom session entries.

## Where to look
- Runtime helpers: `agent_toolkit/compaction/`
- Session entries: `agent_toolkit/session/`
