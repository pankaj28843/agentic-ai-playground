# Assistant Web Backend

Minimal FastAPI backend for the Assistant UI web playground. It provides thread
list operations, message history persistence, and a streaming chat endpoint.

## Development

```bash
uv run --package assistant-web-backend uvicorn assistant_web_backend.main:app --reload --port 10001
```

## Logging

Logs include `request_id` and `trace_id` fields for correlating backend activity with Phoenix traces.
