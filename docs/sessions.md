# Sessions & Branching

The playground stores a **session tree** alongside thread messages to capture branching, labels, and summary metadata.

## Storage model
- Each thread maps to a JSONL session file (under the web storage directory, in `session_tree/`).
- Entries are stored with `id`, `parentId`, `type`, and `timestamp`.
- Message entries use the message `id` as their session entry `id` for stable mapping.

## Entry types
- `message`: User/assistant messages (previewed in the UI).
- `compaction`: Structured summaries and token metadata.
- `branch_summary`: Summaries for a specific branch from a prior entry.
- `label`: Lightweight labels for any entry (used by the UI).
- `custom` / `custom_message`: Extension-driven entries.
- `session_info`, `model_change`, `thinking_level_change`: Runtime metadata entries.

## Branch navigation
- The Session Tree panel highlights the current branch.
- Selecting an entry sets the parent for the next user message, creating a new branch.
- Labels can be added to any entry for quick navigation.

## APIs
- `GET /api/threads/{threadId}/session-tree`
- `POST /api/threads/{threadId}/session-tree/label`

## Notes
- Session tree is designed for fast branch exploration; long-running workflows should still use multiple threads for clarity.
