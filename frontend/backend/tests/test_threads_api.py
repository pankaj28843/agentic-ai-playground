def test_thread_lifecycle(client) -> None:
    create = client.post("/api/threads", json={}).json()
    remote_id = create["remoteId"]

    listed = client.get("/api/threads").json()
    assert listed["threads"][0]["remoteId"] == remote_id

    rename = client.patch(f"/api/threads/{remote_id}", json={"title": "My Run"})
    assert rename.status_code == 200

    archived = client.post(f"/api/threads/{remote_id}/archive")
    assert archived.status_code == 200

    unarchived = client.post(f"/api/threads/{remote_id}/unarchive")
    assert unarchived.status_code == 200

    deleted = client.delete(f"/api/threads/{remote_id}")
    assert deleted.status_code == 200

    listed_after = client.get("/api/threads").json()
    assert listed_after["threads"] == []


def test_messages_and_title(client) -> None:
    remote_id = client.post("/api/threads", json={}).json()["remoteId"]

    message = {
        "id": "msg-1",
        "role": "user",
        "content": [{"type": "text", "text": "Hello there"}],
        "createdAt": "2024-01-15T00:00:00Z",
    }
    append = client.post(
        f"/api/threads/{remote_id}/messages",
        json={"message": message},
    )
    assert append.status_code == 200

    messages = client.get(f"/api/threads/{remote_id}/messages").json()
    assert messages["messages"][0]["id"] == "msg-1"

    title = client.post(
        f"/api/threads/{remote_id}/title",
        json={"messages": [message]},
    ).json()
    assert title["title"] == "Hello there"


def test_profiles_returns_available_profiles(client, monkeypatch) -> None:
    """Test /api/profiles returns profiles when AgentRuntime is available."""
    from unittest.mock import MagicMock

    from assistant_web_backend.services import runtime as runtime_module

    # Create mock public profile
    mock_profile = {
        "id": "test-profile",
        "display_name": "Test Profile",
        "description": "A test profile",
        "entrypoint_type": "single",
        "entrypoint_reference": "general",
        "default": True,
        "metadata": {},
    }

    # Create mock runtime
    mock_runtime = MagicMock()
    mock_runtime.list_public_profiles.return_value = [mock_profile]

    # Mock RuntimeService.get_runtime to return mock
    monkeypatch.setattr(runtime_module.RuntimeService, "get_runtime", lambda: mock_runtime)

    response = client.get("/api/profiles")
    assert response.status_code == 200
    data = response.json()
    assert "profiles" in data
    assert "runModes" in data
    assert len(data["profiles"]) == 1
    assert data["profiles"][0]["id"] == "test-profile"
    assert data["profiles"][0]["name"] == "Test Profile"
    assert data["profiles"][0]["description"] == "A test profile"
    assert data["runModes"] == ["test-profile"]
    assert data["defaultRunMode"] == "test-profile"


def test_profiles_returns_500_when_runtime_unavailable(client, monkeypatch) -> None:
    """Test /api/profiles returns 500 when AgentRuntime is not available."""
    from assistant_web_backend.services import runtime as runtime_module

    # Mock RuntimeService.get_runtime to raise RuntimeError
    def raise_error():
        raise RuntimeError("AgentRuntime not available")

    monkeypatch.setattr(runtime_module.RuntimeService, "get_runtime", raise_error)

    response = client.get("/api/profiles")
    assert response.status_code == 500
    assert "AgentRuntime not available" in response.json()["detail"]


def test_chat_run_streams_response(client, monkeypatch) -> None:
    """Test /api/chat/run streams a response from the agent."""
    from unittest.mock import MagicMock

    from assistant_web_backend.routes import chat as chat_module
    from assistant_web_backend.services import runtime as runtime_module

    # Create mock profile
    mock_profile = MagicMock()
    mock_profile.name = "test-profile"
    mock_profile.model = "bedrock.nova-lite"

    # Create async generator for streaming
    async def mock_stream(*args, **kwargs):
        yield {"data": "Hello"}
        yield {"data": " world"}

    # Create mock runtime
    mock_runtime = MagicMock()
    mock_runtime.list_profiles.return_value = [mock_profile]
    mock_runtime.stream = mock_stream
    mock_runtime.build_invocation_state = MagicMock(return_value={})

    # Mock RuntimeService.get_runtime
    monkeypatch.setattr(runtime_module.RuntimeService, "get_runtime", lambda: mock_runtime)

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.run_mode = "single"
    mock_settings.bedrock_model_id = "bedrock.nova-lite"
    monkeypatch.setattr(chat_module, "load_settings", MagicMock(return_value=mock_settings))

    response = client.post(
        "/api/chat/run",
        json={
            "messages": [
                {
                    "id": "msg-1",
                    "role": "user",
                    "content": [{"type": "text", "text": "Hi"}],
                    "createdAt": "2024-01-15T00:00:00Z",
                }
            ],
            "threadId": "test-thread",
        },
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/jsonl"

    # Check that we got streamed chunks
    lines = response.text.strip().split("\n")
    assert len(lines) >= 1


def test_chat_run_streams_rich_content_with_tool_calls(client, monkeypatch) -> None:
    """Test /api/chat/run streams rich content including tool calls."""
    import json
    from unittest.mock import MagicMock

    from assistant_web_backend.routes import chat as chat_module
    from assistant_web_backend.services import runtime as runtime_module

    # Create mock profile
    mock_profile = MagicMock()
    mock_profile.name = "test-profile"
    mock_profile.model = "bedrock.nova-lite"

    # Create async generator that simulates tool call events
    async def mock_stream(*args, **kwargs):
        # First, emit some text
        yield {"data": "Searching..."}
        # Then emit a tool call start
        yield {
            "current_tool_use": {
                "name": "search",
                "input": {"query": "test"},
                "toolUseId": "tc-123",
            }
        }
        # Then emit tool result
        yield {"tool_result": {"found": True}}
        # Then emit more text
        yield {"data": " Found it!"}

    # Create mock runtime
    mock_runtime = MagicMock()
    mock_runtime.list_profiles.return_value = [mock_profile]
    mock_runtime.stream = mock_stream
    mock_runtime.build_invocation_state = MagicMock(return_value={})

    # Mock RuntimeService.get_runtime
    monkeypatch.setattr(runtime_module.RuntimeService, "get_runtime", lambda: mock_runtime)

    # Mock settings
    mock_settings = MagicMock()
    mock_settings.run_mode = "single"
    mock_settings.bedrock_model_id = "bedrock.nova-lite"
    monkeypatch.setattr(chat_module, "load_settings", MagicMock(return_value=mock_settings))

    response = client.post(
        "/api/chat/run",
        json={
            "messages": [
                {
                    "id": "msg-1",
                    "role": "user",
                    "content": [{"type": "text", "text": "Search for test"}],
                    "createdAt": "2024-01-15T00:00:00Z",
                }
            ],
            "threadId": "test-thread",
        },
    )
    assert response.status_code == 200

    # Parse streamed chunks and verify rich content structure
    lines = [ln for ln in response.text.strip().split("\n") if ln.strip()]
    assert len(lines) >= 1

    # The streaming response should contain content arrays
    for line in lines:
        chunk = json.loads(line)
        # Each chunk should have a content array
        assert "content" in chunk
        assert isinstance(chunk["content"], list)
        # Each part should have a type
        for part in chunk["content"]:
            assert "type" in part
            assert part["type"] in ("text", "tool-call", "reasoning")


def test_chat_run_persists_thread_overrides(client, monkeypatch) -> None:
    """Test that overrides from /api/chat/run are persisted to thread metadata."""
    from unittest.mock import MagicMock

    from assistant_web_backend.routes import chat as chat_module
    from assistant_web_backend.services import runtime as runtime_module

    mock_profile = MagicMock()
    mock_profile.name = "test-profile"
    mock_profile.model = "bedrock.nova-lite"

    async def mock_stream(*args, **kwargs):
        yield {"data": "Hello"}

    mock_runtime = MagicMock()
    mock_runtime.list_profiles.return_value = [mock_profile]
    mock_runtime.stream = mock_stream
    mock_runtime.build_invocation_state = MagicMock(return_value={})

    monkeypatch.setattr(runtime_module.RuntimeService, "get_runtime", lambda: mock_runtime)

    mock_settings = MagicMock()
    mock_settings.run_mode = "single"
    mock_settings.bedrock_model_id = "bedrock.nova-lite"
    monkeypatch.setattr(chat_module, "load_settings", MagicMock(return_value=mock_settings))

    response = client.post(
        "/api/chat/run",
        json={
            "messages": [
                {
                    "id": "msg-1",
                    "role": "user",
                    "content": [{"type": "text", "text": "Hi"}],
                    "createdAt": "2024-01-15T00:00:00Z",
                }
            ],
            "threadId": "thread-override",
            "modelOverride": "bedrock.nova-pro",
            "toolGroupsOverride": ["techdocs"],
        },
    )
    assert response.status_code == 200
    _ = response.text

    detail = client.get("/api/threads/thread-override").json()
    assert detail["modelOverride"] == "bedrock.nova-pro"
    assert detail["toolGroupsOverride"] == ["techdocs"]


def test_chat_run_inference_profile_error_is_friendly(client, monkeypatch) -> None:
    """Test inference profile errors are mapped to a friendly message."""
    from unittest.mock import MagicMock

    from assistant_web_backend.routes import chat as chat_module
    from assistant_web_backend.services import runtime as runtime_module

    mock_profile = MagicMock()
    mock_profile.name = "test-profile"
    mock_profile.model = "bedrock.nova-lite"

    async def mock_stream(*args, **kwargs):
        raise RuntimeError(
            "Invocation of model ID anthropic.claude-haiku-4-5-20251001-v1:0 with on-demand throughput isn't supported."
        )
        yield {"data": "unreachable"}

    mock_runtime = MagicMock()
    mock_runtime.list_profiles.return_value = [mock_profile]
    mock_runtime.stream = mock_stream
    mock_runtime.build_invocation_state = MagicMock(return_value={})

    monkeypatch.setattr(runtime_module.RuntimeService, "get_runtime", lambda: mock_runtime)

    mock_settings = MagicMock()
    mock_settings.run_mode = "single"
    mock_settings.bedrock_model_id = "bedrock.nova-lite"
    monkeypatch.setattr(chat_module, "load_settings", MagicMock(return_value=mock_settings))

    response = client.post(
        "/api/chat/run",
        json={
            "messages": [
                {
                    "id": "msg-1",
                    "role": "user",
                    "content": [{"type": "text", "text": "Hi"}],
                    "createdAt": "2024-01-15T00:00:00Z",
                }
            ],
            "threadId": "thread-error",
        },
    )
    assert response.status_code == 200
    assert "inference profile" in response.text.lower()


def test_chat_run_requires_runtime(client, monkeypatch) -> None:
    """Test /api/chat/run raises when runtime is unavailable."""
    import pytest
    from assistant_web_backend.services import runtime as runtime_module

    # Mock RuntimeService.get_runtime to raise RuntimeError
    def raise_error():
        raise RuntimeError("AgentRuntime not available")

    monkeypatch.setattr(runtime_module.RuntimeService, "get_runtime", raise_error)

    # The error should propagate through the streaming response
    with pytest.raises(RuntimeError, match="AgentRuntime not available"):
        client.post(
            "/api/chat/run",
            json={
                "messages": [
                    {
                        "id": "msg-1",
                        "role": "user",
                        "content": [{"type": "text", "text": "Hi"}],
                        "createdAt": "2024-01-15T00:00:00Z",
                    }
                ],
            },
        )


def test_thread_rename_validation(client) -> None:
    """Test ThreadRenameRequest title validation."""
    remote_id = client.post("/api/threads", json={}).json()["remoteId"]

    # Empty title should fail validation
    response = client.patch(f"/api/threads/{remote_id}", json={"title": ""})
    assert response.status_code == 422

    # Title too long should fail validation
    long_title = "a" * 201
    response = client.patch(f"/api/threads/{remote_id}", json={"title": long_title})
    assert response.status_code == 422

    # Valid title should work
    response = client.patch(f"/api/threads/{remote_id}", json={"title": "Valid title"})
    assert response.status_code == 200


def test_message_role_validation(client) -> None:
    """Test MessagePayload role validation with Literal type."""
    remote_id = client.post("/api/threads", json={}).json()["remoteId"]

    # Valid role should work
    valid_message = {
        "id": "msg-valid",
        "role": "user",
        "content": [{"type": "text", "text": "Hello"}],
        "createdAt": "2024-01-15T00:00:00Z",
    }
    response = client.post(f"/api/threads/{remote_id}/messages", json={"message": valid_message})
    assert response.status_code == 200

    # Invalid role should fail
    invalid_message = {
        "id": "msg-invalid",
        "role": "invalid_role",
        "content": [{"type": "text", "text": "Hello"}],
        "createdAt": "2024-01-15T00:00:00Z",
    }
    response = client.post(f"/api/threads/{remote_id}/messages", json={"message": invalid_message})
    assert response.status_code == 422


def test_message_with_tool_call_content(client) -> None:
    """Test that messages with tool call content are persisted correctly."""
    remote_id = client.post("/api/threads", json={}).json()["remoteId"]

    # Create message with tool call content part
    message = {
        "id": "msg-tool",
        "role": "assistant",
        "content": [
            {"type": "text", "text": "I'll search for that."},
            {
                "type": "tool-call",
                "toolCallId": "tc-123",
                "toolName": "search",
                "args": {"query": "test"},
                "argsText": '{"query": "test"}',
                "result": {"found": True},
                "isError": False,
            },
        ],
        "createdAt": "2024-01-15T00:00:00Z",
    }
    append = client.post(f"/api/threads/{remote_id}/messages", json={"message": message})
    assert append.status_code == 200

    # Retrieve and verify content is preserved
    messages = client.get(f"/api/threads/{remote_id}/messages").json()
    stored = messages["messages"][0]
    assert stored["id"] == "msg-tool"
    assert len(stored["content"]) == 2

    # Verify text part
    assert stored["content"][0]["type"] == "text"
    assert stored["content"][0]["text"] == "I'll search for that."

    # Verify tool call part
    tool_part = stored["content"][1]
    assert tool_part["type"] == "tool-call"
    assert tool_part["toolCallId"] == "tc-123"
    assert tool_part["toolName"] == "search"
    assert tool_part["args"] == {"query": "test"}
    assert tool_part["result"] == {"found": True}
    assert tool_part["isError"] is False


def test_message_with_reasoning_content(client) -> None:
    """Test that messages with reasoning content are persisted correctly."""
    remote_id = client.post("/api/threads", json={}).json()["remoteId"]

    # Create message with reasoning content part
    message = {
        "id": "msg-reason",
        "role": "assistant",
        "content": [
            {"type": "reasoning", "text": "Let me think about this..."},
            {"type": "text", "text": "Here's my answer."},
        ],
        "createdAt": "2024-01-15T00:00:00Z",
    }
    append = client.post(f"/api/threads/{remote_id}/messages", json={"message": message})
    assert append.status_code == 200

    # Retrieve and verify content is preserved
    messages = client.get(f"/api/threads/{remote_id}/messages").json()
    stored = messages["messages"][0]
    assert len(stored["content"]) == 2

    # Verify reasoning part
    assert stored["content"][0]["type"] == "reasoning"
    assert stored["content"][0]["text"] == "Let me think about this..."

    # Verify text part
    assert stored["content"][1]["type"] == "text"
    assert stored["content"][1]["text"] == "Here's my answer."
