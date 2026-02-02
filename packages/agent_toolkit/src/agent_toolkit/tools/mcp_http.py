"""MCP HTTP client for resources and prompts.

This module provides a simple JSON-RPC client for MCP server features
that aren't tool calls (resources, prompts). For tool calls, the Strands
MCPClient is used directly - see mcp/providers.py.
"""

from __future__ import annotations

import json
from itertools import count
from typing import Any

import httpx


class MCPHttpClient:
    """Minimal MCP HTTP client for JSON-RPC requests."""

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        """Initialize the HTTP client."""
        self._base_url = base_url
        self._counter = count(1)
        self._client = client or httpx.AsyncClient(base_url=base_url, timeout=30.0)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def request(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        request_id = next(self._counter)
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        response = await self._client.post(
            "",
            json=payload,
            headers={"Accept": "application/json, text/event-stream"},
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if content_type.startswith("text/event-stream"):
            data = await _read_sse_json(response)
        else:
            data = response.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        result = data.get("result", {})
        _raise_for_tool_error(result)
        return result


async def _read_sse_json(response: httpx.Response) -> dict[str, Any]:
    """Read JSON from SSE response."""
    payloads: list[dict[str, Any]] = []
    async for line in response.aiter_lines():
        if not line.startswith("data:"):
            continue
        data = line.removeprefix("data:").strip()
        if not data or data == "[DONE]":
            continue
        try:
            parsed = json.loads(data)
            payloads.append(parsed)
        except json.JSONDecodeError:
            pass
    return payloads[-1] if payloads else {}


def _raise_for_tool_error(result: dict[str, Any]) -> None:
    """Raise if MCP result indicates an error."""
    if not result.get("isError"):
        return
    content = result.get("content", [])
    for entry in content:
        if "text" in entry:
            raise RuntimeError(str(entry["text"]))
        if "json" in entry:
            raise RuntimeError(json.dumps(entry["json"], ensure_ascii=True))
    error_msg = "MCP tool call failed"
    raise RuntimeError(error_msg)
