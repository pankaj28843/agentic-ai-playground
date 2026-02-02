import json

import httpx
import pytest
from agent_toolkit.tools.mcp_http import MCPHttpClient


@pytest.mark.asyncio
async def test_mcp_http_client_parses_sse() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        data = {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
        payload = f"data: {json.dumps(data)}\n\n"
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            text=payload,
        )

    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient(transport=transport, base_url="http://test")
    client = MCPHttpClient("http://test", client=async_client)
    result = await client.request("tools/list")
    await client.close()
    assert result == {"tools": []}


@pytest.mark.asyncio
async def test_mcp_http_client_raises_tool_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "result": {
                    "content": [{"type": "text", "text": "boom"}],
                    "isError": True,
                },
            },
        )

    transport = httpx.MockTransport(handler)
    async_client = httpx.AsyncClient(transport=transport, base_url="http://test")
    client = MCPHttpClient("http://test", client=async_client)
    with pytest.raises(RuntimeError, match="boom"):
        await client.request("tools/call")
    await client.close()
