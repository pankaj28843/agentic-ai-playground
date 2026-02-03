#!/usr/bin/env python3
"""Consolidated E2E tests for run modes, metadata, memory, and tool usage."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

import httpx

DEFAULT_BASE_URL = os.getenv("E2E_BASE_URL", "")
DEFAULT_TIMEOUT = 180.0


@dataclass
class StreamResult:
    """Captured result from streaming chat API."""

    text_parts: list[str] = field(default_factory=list)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    agent_events: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Get concatenated text from all text parts."""
        return "".join(self.text_parts)


def create_message(role: str, text: str) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "role": role,
        "content": [{"type": "text", "text": text}],
        "createdAt": datetime.now(UTC).isoformat(),
    }


def get_profiles(base_url: str, timeout: float) -> dict[str, Any]:
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(f"{base_url}/api/profiles")
        resp.raise_for_status()
        return resp.json()


def resolve_run_mode(data: dict[str, Any], entrypoint_type: str | None = None) -> str | None:
    profiles = data.get("profiles", [])
    if entrypoint_type:
        match = next(
            (profile for profile in profiles if profile.get("entrypointType") == entrypoint_type),
            None,
        )
        if match:
            return match.get("id")
    return data.get("defaultRunMode") or (data.get("runModes") or [None])[0]


def resolve_run_mode_by_name(data: dict[str, Any], name: str) -> str | None:
    target = name.strip().lower()
    profiles = data.get("profiles", [])
    for profile in profiles:
        if profile.get("id", "").lower() == target or profile.get("name", "").lower() == target:
            return profile.get("id")
    return None


def stream_chat(
    base_url: str,
    timeout: float,
    thread_id: str,
    messages: list[dict[str, Any]],
    run_mode: str,
) -> StreamResult:
    payload = {
        "messages": messages,
        "threadId": thread_id,
        "runMode": run_mode,
    }

    result = StreamResult()

    with (
        httpx.Client(timeout=timeout) as client,
        client.stream("POST", f"{base_url}/api/chat/run", json=payload) as resp,
    ):
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line.strip():
                continue
            with contextlib.suppress(json.JSONDecodeError):
                chunk = json.loads(line)
                for part in chunk.get("content", []):
                    part_type = part.get("type")
                    if part_type == "text" and part.get("text"):
                        text = part.get("text")
                        result.text_parts.append(text)
                        if "Agent error:" in text:
                            result.errors.append(text)
                    elif part_type == "tool-call":
                        result.tool_calls.append(part)
                    elif part_type == "tool-result":
                        result.tool_results.append(part)
                    elif part_type == "agent-event":
                        result.agent_events.append(part)

                for key in (
                    "phoenixTraceId",
                    "phoenixSessionId",
                    "runMode",
                    "profileName",
                    "modelId",
                    "executionMode",
                    "entrypointReference",
                ):
                    if chunk.get(key) is not None:
                        result.metadata[key] = chunk.get(key)

    return result


def test_profiles_api(base_url: str, timeout: float) -> bool:
    print("[profiles] checking /api/profiles")
    data = get_profiles(base_url, timeout)
    profiles = data.get("profiles", [])
    run_modes = data.get("runModes", [])
    if not profiles or not run_modes:
        print("❌ profiles or run modes missing")
        return False
    profile_ids = [profile.get("id") for profile in profiles]
    for profile_id in profile_ids:
        if profile_id not in run_modes:
            print(f"❌ runModes missing profile id: {profile_id}")
            return False
    print(f"✅ profiles: {len(profiles)} modes: {len(run_modes)}")
    return True


def test_mode_switching(base_url: str, timeout: float) -> bool:
    print("[modes] switching modes within one thread")
    data = get_profiles(base_url, timeout)
    run_modes = data.get("runModes", [])
    if not run_modes:
        print("❌ no run modes")
        return False

    thread_id = str(uuid.uuid4())
    modes_to_test = run_modes[:3]
    for run_mode in modes_to_test:
        result = stream_chat(
            base_url,
            timeout,
            thread_id,
            [create_message("user", f"Mode {run_mode}: what is Django?")],
            run_mode,
        )
        if result.errors or not result.text:
            print(f"❌ empty response for {run_mode}")
            return False
        if result.metadata.get("runMode") != run_mode:
            print(f"❌ runMode mismatch for {run_mode}: {result.metadata.get('runMode')}")
            return False
        if not result.metadata.get("executionMode"):
            print(f"❌ missing executionMode for {run_mode}")
            return False
        if not result.metadata.get("entrypointReference"):
            print(f"❌ missing entrypointReference for {run_mode}")
            return False
        print(
            f"✅ {run_mode}: execution={result.metadata.get('executionMode')} entrypoint={result.metadata.get('entrypointReference')}"
        )
    return True


def test_metadata_persistence(base_url: str, timeout: float) -> bool:
    print("[metadata] persistence in thread storage")
    data = get_profiles(base_url, timeout)
    run_mode = resolve_run_mode(data)
    if not run_mode:
        print("❌ no run mode available")
        return False

    thread_id = str(uuid.uuid4())
    user_msg = create_message("user", "What is FastAPI?")
    result = stream_chat(
        base_url,
        timeout,
        thread_id,
        [user_msg],
        run_mode,
    )
    if result.errors:
        print(f"❌ stream error: {result.errors[0]}")
        return False

    # Persist the assistant message to storage (simulating frontend behavior)
    assistant_msg = {
        "id": str(uuid.uuid4()),
        "role": "assistant",
        "content": [{"type": "text", "text": result.text[:1000]}],
        "createdAt": datetime.now(UTC).isoformat(),
    }
    with httpx.Client(timeout=timeout) as client:
        # First persist user message
        client.post(
            f"{base_url}/api/threads/{thread_id}/messages",
            json={"message": user_msg},
        )
        # Then persist assistant message with metadata
        resp = client.post(
            f"{base_url}/api/threads/{thread_id}/messages",
            json={
                "message": assistant_msg,
                "runMode": result.metadata.get("runMode"),
                "executionMode": result.metadata.get("executionMode"),
                "entrypointReference": result.metadata.get("entrypointReference"),
                "phoenixTraceId": result.metadata.get("phoenixTraceId"),
            },
        )
        if resp.status_code >= 400:
            print(f"❌ failed to persist message: {resp.status_code}")
            return False

        # Now fetch messages
        resp = client.get(f"{base_url}/api/threads/{thread_id}/messages")
        resp.raise_for_status()
        messages = resp.json().get("messages", [])

    assistant_message = next((msg for msg in messages if msg.get("role") == "assistant"), None)
    if not assistant_message:
        print("❌ missing assistant message")
        return False

    required_fields = ["runMode", "executionMode", "entrypointReference"]
    missing = [field for field in required_fields if not assistant_message.get(field)]
    if missing:
        print(f"❌ missing persisted metadata: {missing}")
        return False

    print("✅ metadata persisted")
    return True


def test_settings_api(base_url: str, timeout: float) -> bool:
    print("[settings] verify settings metadata endpoint")
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(f"{base_url}/api/settings")
        resp.raise_for_status()
        payload = resp.json()

    tool_groups = payload.get("toolGroups", [])
    if not tool_groups:
        print("❌ settings missing tool groups")
        return False
    print(f"✅ settings tool groups: {len(tool_groups)}")
    return True


def test_session_tree_api(base_url: str, timeout: float) -> bool:
    print("[sessions] verify session tree endpoint")
    thread_id = str(uuid.uuid4())
    user_msg = create_message("user", "Session tree entry one")
    assistant_msg = create_message("assistant", "Session tree entry two")

    with httpx.Client(timeout=timeout) as client:
        client.post(f"{base_url}/api/threads/{thread_id}/messages", json={"message": user_msg})
        client.post(f"{base_url}/api/threads/{thread_id}/messages", json={"message": assistant_msg})
        resp = client.get(f"{base_url}/api/threads/{thread_id}/session-tree")
        if resp.status_code >= 400:
            print(f"❌ session tree fetch failed: {resp.status_code}")
            return False
        data = resp.json()

    entries = data.get("entries", [])
    if len(entries) < 2:
        print("❌ session tree entries missing")
        return False

    print(f"✅ session tree entries: {len(entries)}")
    return True


def test_memory_single(base_url: str, timeout: float) -> bool:
    print("[memory] recall in single-entrypoint mode")
    data = get_profiles(base_url, timeout)
    run_mode = resolve_run_mode(data, "single")
    if not run_mode:
        print("⚠️ no single-entrypoint profile; skipping")
        return True

    thread_id = str(uuid.uuid4())
    msg1 = create_message("user", "The framework I am learning is Django. Remember that.")
    response1 = stream_chat(base_url, timeout, thread_id, [msg1], run_mode)
    if response1.errors:
        print(f"❌ first turn error: {response1.errors[0]}")
        return False

    assistant_msg = create_message("assistant", response1.text[:10000])
    msg2 = create_message("user", "What framework am I learning?")
    response2 = stream_chat(base_url, timeout, thread_id, [msg1, assistant_msg, msg2], run_mode)
    if response2.errors:
        print(f"❌ second turn error: {response2.errors[0]}")
        return False

    if "django" not in response2.text.lower():
        print("❌ recall failed")
        return False

    print("✅ recall passed")
    return True


def test_plan_mode_read_only(base_url: str, timeout: float) -> bool:
    print("[plan] verify plan mode is read-only")
    data = get_profiles(base_url, timeout)
    run_mode = resolve_run_mode_by_name(data, "plan")
    if not run_mode:
        print("❌ plan mode profile missing")
        return False

    thread_id = str(uuid.uuid4())
    result = stream_chat(
        base_url,
        timeout,
        thread_id,
        [
            create_message(
                "user",
                "Create a refactor plan for this repo. Do not execute steps or modify files. End with [DONE:0].",
            )
        ],
        run_mode,
    )
    if result.errors:
        print(f"❌ plan mode error: {result.errors[0]}")
        return False

    if "[done:" not in result.text.lower():
        print("❌ plan mode response missing [DONE:0] marker")
        return False

    blocked_tools = {"file_write", "editor", "shell"}
    for part in result.tool_calls + result.tool_results:
        name = part.get("toolName") or part.get("tool_name") or part.get("name")
        if name in blocked_tools:
            print(f"❌ plan mode invoked blocked tool: {name}")
            return False

    print("✅ plan mode read-only flow passed")
    return True


def test_tool_calls(base_url: str, timeout: float) -> bool:
    print("[tools] verify TechDocs tool calls")
    data = get_profiles(base_url, timeout)
    run_mode = resolve_run_mode(data)
    if not run_mode:
        print("❌ no run mode available")
        return False

    thread_id = str(uuid.uuid4())
    result = stream_chat(
        base_url,
        timeout,
        thread_id,
        [
            create_message(
                "user", "Search TechDocs for: Django QuerySet annotate example. Call the tool now."
            )
        ],
        run_mode,
    )
    if result.errors:
        print(f"❌ tool test error: {result.errors[0]}")
        return False

    if not result.tool_calls and not result.tool_results:
        print("❌ no tool calls detected")
        return False

    print(f"✅ tool calls: {len(result.tool_calls) + len(result.tool_results)}")
    return True


def test_subagent_tool(base_url: str, timeout: float) -> bool:
    print("[subagents] verify subagent tool invocation")
    data = get_profiles(base_url, timeout)
    run_mode = resolve_run_mode(data, "single")
    if not run_mode:
        print("❌ no single-entrypoint profile")
        return False

    thread_id = str(uuid.uuid4())
    result = stream_chat(
        base_url,
        timeout,
        thread_id,
        [
            create_message(
                "user",
                "Call the subagent tool in chain mode with two tasks: "
                "agent='scout' prompt='Summarize the repo goal.' "
                "agent='planner' prompt='Create a short plan based on the scout summary.'",
            )
        ],
        run_mode,
    )
    if result.errors:
        print(f"❌ subagent tool error: {result.errors[0]}")
        return False

    tool_names = [
        part.get("toolName") or part.get("tool_name") or part.get("name")
        for part in (result.tool_calls + result.tool_results)
    ]
    if "subagent" not in tool_names:
        print("❌ subagent tool call not detected")
        return False

    print("✅ subagent tool call detected")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Consolidated E2E tests")
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Base URL for the web backend (or set E2E_BASE_URL).",
    )
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    parser.add_argument("--skip-tools", action="store_true")
    args = parser.parse_args()
    if not args.base_url:
        parser.error("Base URL required. Pass --base-url or set E2E_BASE_URL.")

    tests = [
        test_profiles_api,
        test_mode_switching,
        test_metadata_persistence,
        test_settings_api,
        test_session_tree_api,
        test_plan_mode_read_only,
        test_memory_single,
    ]
    if not args.skip_tools:
        tests.append(test_tool_calls)
        tests.append(test_subagent_tool)

    failures = 0
    for test_fn in tests:
        ok = test_fn(args.base_url, args.timeout)
        if not ok:
            failures += 1

    if failures:
        print(f"❌ {failures} test(s) failed")
        return 1
    print("✅ all tests passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
