#!/usr/bin/env python3
"""Non-interactive debug runner for the TUI agent runtime."""

from __future__ import annotations

import argparse
import asyncio
import re
import sys

from agent_toolkit import AgentRuntime


def _write_line(message: str) -> None:
    sys.stdout.write(f"{message}\n")
    sys.stdout.flush()


def _format_trace_tool(payload: object) -> str:
    tool_use = payload if isinstance(payload, dict) else {"name": str(payload)}
    name = str(tool_use.get("name", "tool"))
    tool_input = str(tool_use.get("input", ""))
    if tool_input:
        preview = tool_input.replace("\n", " ")[:160]
        return f"tool call -> {name} input={preview}"
    return f"tool call -> {name}"


def _format_trace_output(payload: object) -> str:
    output = payload.get("output") if isinstance(payload, dict) else payload
    output_text = str(output or "").replace("\n", " ")
    preview = output_text[:200]
    if not preview:
        return "tool output: (empty)"
    return f"tool output ({len(output_text)} chars): {preview}"


def _format_empty_stream(last_tool_output: str) -> str:
    if last_tool_output:
        return f"No response returned. Latest tool output:\n{last_tool_output}"
    return "No response returned. Check the tool log for details."


def _strip_thinking(text: str, in_thinking: bool) -> tuple[str, bool]:
    if "<thinking" in text and "</thinking>" in text:
        cleaned = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
        return cleaned, in_thinking
    output: list[str] = []
    i = 0
    while i < len(text):
        start = text.find("<thinking", i)
        end = text.find("</thinking>", i)
        if in_thinking:
            if end == -1:
                return "".join(output), True
            i = end + len("</thinking>")
            in_thinking = False
            continue
        if start == -1:
            output.append(text[i:])
            break
        output.append(text[i:start])
        close = text.find(">", start)
        if close == -1:
            return "".join(output), True
        in_thinking = True
        i = close + 1
    return "".join(output), in_thinking


def _process_stream_chunk(chunk: str, in_thinking: bool) -> tuple[str, bool, bool]:
    printed_output = bool(chunk.strip())
    if "thinking" in chunk:
        return "", False, printed_output
    if in_thinking:
        return "", in_thinking, printed_output
    cleaned, in_thinking = _strip_thinking(chunk, in_thinking)
    return cleaned, in_thinking, printed_output


async def _run_preflight() -> None:
    """Run a preflight check by testing the MCP connection."""
    # Simple preflight: verify we can create a runtime and list profiles
    try:
        runtime = AgentRuntime()
        profiles = runtime.list_public_profiles()
        _write_line(f"preflight passed: {len(profiles)} public profiles available")
        if profiles:
            default_profile = next(
                (p["id"] for p in profiles if p.get("default")), profiles[0]["id"]
            )
            _write_line(f"default run mode: {default_profile}")
    except Exception as exc:  # noqa: BLE001 - debug helper
        _write_line(f"preflight error: {exc}")
        return


async def _run_stream(args: argparse.Namespace) -> int:
    runtime = AgentRuntime()
    invocation_state = runtime.build_invocation_state(
        args.resource,
        args.session,
        run_mode=args.run_mode,
        profile_name=args.run_mode,
    )
    output_buffer: list[str] = []
    last_tool_output = ""
    in_thinking = False
    printed_output = False
    _write_line("[trace] working...")

    # Convert prompt string to message format expected by stream()
    messages: list[dict[str, object]] = [{"role": "user", "content": [{"text": args.prompt}]}]

    try:
        async for event in runtime.stream(
            args.run_mode,
            args.run_mode,
            messages,
            invocation_state,
            args.session,
        ):
            if "data" in event:
                chunk = str(event["data"])
                cleaned, in_thinking, saw_output = _process_stream_chunk(
                    chunk,
                    in_thinking,
                )
                if saw_output:
                    printed_output = True
                if cleaned:
                    output_buffer.append(cleaned)
                    sys.stdout.write(cleaned)
                    sys.stdout.flush()
            if "current_tool_use" in event:
                _write_line(f"\n[trace] {_format_trace_tool(event['current_tool_use'])}")
            if "tool_result" in event or "tool_output" in event:
                payload = event.get("tool_result") or event.get("tool_output") or ""
                last_tool_output = str(payload or "")
                printed_output = True
                _write_line(f"\n[trace] {_format_trace_output({'output': payload})}")
            if "error" in event:
                _write_line(f"\n[error] {event['error']}")
            if event.get("complete"):
                break
    except Exception as exc:  # noqa: BLE001 - debug helper
        _write_line(f"\n[error] {exc}")
        return 1

    if not printed_output and not "".join(output_buffer).strip():
        _write_line(f"\n{_format_empty_stream(last_tool_output)}")
        return 1
    return 0


def _run_once(args: argparse.Namespace) -> int:
    runtime = AgentRuntime()
    invocation_state = runtime.build_invocation_state(
        args.resource,
        args.session,
        run_mode=args.run_mode,
        profile_name=args.run_mode,
    )
    result = runtime.run(
        args.run_mode,
        args.run_mode,
        args.prompt,
        invocation_state,
        args.session,
    )
    output = str(result)
    _write_line(output)
    if not output.strip():
        _write_line(_format_empty_stream(""))
        return 1
    return 0


async def main() -> int:
    """Run the non-interactive debug flow."""
    parser = argparse.ArgumentParser(
        description="Debug the agent runtime without the TUI.",
    )
    parser.add_argument(
        "--prompt",
        default="list tenants (first 10)",
        help="Prompt to send to the agent.",
    )
    parser.add_argument(
        "--run-mode",
        default="",
        help="Public profile name (run mode) to execute.",
    )
    parser.add_argument(
        "--session",
        default="",
        help="Optional session id.",
    )
    parser.add_argument(
        "--resource",
        default="",
        help="Optional resource URI to pass to the runtime.",
    )
    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming and run a single request.",
    )
    parser.add_argument(
        "--preflight",
        action="store_true",
        help="Run TechDocs MCP preflight before the prompt.",
    )
    args = parser.parse_args()

    if args.preflight:
        await _run_preflight()

    if not args.run_mode:
        runtime = AgentRuntime()
        profiles = runtime.list_public_profiles()
        if not profiles:
            _write_line("error: no public profiles configured")
            return 1
        args.run_mode = next((p["id"] for p in profiles if p.get("default")), profiles[0]["id"])

    if args.no_stream:
        return _run_once(args)
    return await _run_stream(args)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
