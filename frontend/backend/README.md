# Assistant Web Backend

Minimal FastAPI backend for the Assistant UI web playground. It provides thread
list operations, message history persistence, and a streaming chat endpoint.

## Development

```bash
uv run --package assistant-web-backend uvicorn assistant_web_backend.main:app --reload --port 10001
```
