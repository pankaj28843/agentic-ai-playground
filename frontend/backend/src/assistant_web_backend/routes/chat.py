"""Chat streaming routes."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from agent_toolkit.config import load_settings
from agent_toolkit.telemetry import EvalConfig, OnlineEvaluator
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from assistant_web_backend.models.messages import ContentPart, MessagePayload, RichStreamChunk
from assistant_web_backend.models.threads import ChatRunRequest
from assistant_web_backend.services.runtime import RuntimeService
from assistant_web_backend.services.streaming import StreamState

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

# Module-level evaluator instance (lazily initialized)
_online_evaluator: OnlineEvaluator | None = None

# Background tasks set to keep references (prevents garbage collection)
_background_tasks: set[asyncio.Task[None]] = set()


def _get_evaluator() -> OnlineEvaluator:
    """Get or create the online evaluator singleton."""
    global _online_evaluator  # noqa: PLW0603
    if _online_evaluator is None:
        settings = load_settings()
        config = EvalConfig.from_settings(settings)
        _online_evaluator = OnlineEvaluator(config)
    return _online_evaluator


def _schedule_background_task(coro: Any) -> None:
    """Schedule a background task and track it to prevent GC."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat/run")
def run_chat(payload: ChatRunRequest) -> StreamingResponse:
    """Stream a chat response for the provided messages."""
    thread_id = payload.thread_id or ""

    async def stream() -> AsyncGenerator[bytes]:
        async for chunk in _run_stream(thread_id, payload):
            yield chunk

    return StreamingResponse(stream(), media_type="application/jsonl")


def _extract_phoenix_metadata(event: Any) -> str | None:
    """Extract Phoenix trace ID from any event."""
    if isinstance(event, dict) and event.get("phoenix_trace_id"):
        return event.get("phoenix_trace_id")
    return None


def _extract_message_id(messages: list[MessagePayload]) -> str | None:
    """Extract the most recent user message id for trace correlation."""
    for message in reversed(messages):
        if message.role == "user":
            return message.id
    if messages:
        return messages[-1].id
    return None


async def _run_stream(  # noqa: C901, PLR0912
    thread_id: str,
    payload: ChatRunRequest,
) -> AsyncGenerator[bytes]:
    """Run the agent stream and yield encoded chunks."""
    runtime = RuntimeService.get_runtime()
    settings = load_settings()
    profiles = runtime.list_profiles()

    from agent_toolkit.config.execution_mode import get_execution_mode_resolver  # noqa: PLC0415

    resolver = get_execution_mode_resolver()
    run_mode = payload.run_mode or resolver.get_default_profile() or settings.run_mode
    if not run_mode:
        msg = "No public profiles configured; run_mode is required"
        raise RuntimeError(msg)

    # Resolve execution metadata using the public profile
    try:
        execution_mode, entrypoint_reference, _resolved_metadata = resolver.resolve_execution_mode(
            run_mode
        )
    except (RuntimeError, ValueError) as e:
        logger.exception("Failed to resolve execution mode for profile '%s'", run_mode)
        yield _encode_rich_chunk(
            [ContentPart(type="text", text=f"Agent error: {e}")],
            run_mode=run_mode,
        )
        return

    # Map to actual agent profile (single mode only)
    model_id = None
    if execution_mode == "single":
        profile = next((p for p in profiles if p.name == entrypoint_reference), None)
        model_id = profile.model if profile and profile.model else settings.bedrock_model_id

    state = StreamState()
    captured_trace_id: str | None = None
    user_input: str = ""

    # Extract user input for evaluation
    for msg in payload.messages:
        if msg.role == "user":
            for part in msg.content:
                if part.get("type") == "text":
                    user_input = part.get("text", "")

    strands_messages, conversion_stats = _convert_to_strands_messages(
        payload.messages,
        compact_tools=True,
    )
    logger.info(
        "Converted %d messages for thread %s (tools stripped: %d, results kept: %d)",
        conversion_stats["message_count"],
        thread_id,
        conversion_stats["tool_calls_stripped"],
        conversion_stats["tool_results_kept"],
    )

    message_id = _extract_message_id(payload.messages) or ""
    invocation_state = runtime.build_invocation_state(
        "",
        thread_id or f"thread-{run_mode}",
        thread_id=thread_id or "",
        message_id=message_id,
        run_mode=run_mode,
        profile_name=run_mode,
    )

    try:
        async for event in runtime.stream(
            mode=run_mode,
            profile_name=run_mode,
            messages=strands_messages,
            invocation_state=invocation_state,
            session_id=thread_id or f"thread-{run_mode}",
        ):
            # Capture Phoenix metadata from any event (not just stream_metadata)
            trace_id_from_event = _extract_phoenix_metadata(event)
            if trace_id_from_event:
                captured_trace_id = trace_id_from_event
                logger.debug("Captured Phoenix trace_id from event: %s", captured_trace_id)

            # Skip stream_metadata events (they're just for metadata)
            if isinstance(event, dict) and event.get("type") == "stream_metadata":
                continue

            event_data = _normalize_event(event)
            if event_data and state.handle_event(event_data):
                # Include Phoenix metadata in every chunk if available
                yield _encode_rich_chunk(
                    state.build_content(),
                    trace_id=captured_trace_id if captured_trace_id else None,
                    session_id=thread_id or None,
                )

        yield _encode_rich_chunk(
            state.build_content(),
            trace_id=captured_trace_id,
            session_id=thread_id or None,
            run_mode=run_mode,
            profile_name=entrypoint_reference,
            model_id=model_id,
            execution_mode=execution_mode,
            entrypoint_reference=entrypoint_reference,
        )

        # Run online evaluation asynchronously (non-blocking)
        response_text = state.get_text_content()
        if response_text and user_input:
            _schedule_background_task(_run_evaluation(user_input, response_text, captured_trace_id))
    except Exception as exc:
        logger.exception("Agent stream failed")
        yield _encode_rich_chunk([ContentPart(type="text", text=f"Agent error: {exc}")])


async def _run_evaluation(
    user_input: str,
    response_text: str,
    trace_id: str | None,
) -> None:
    """Run online evaluation in background."""
    evaluator = _get_evaluator()
    if not evaluator.enabled:
        return

    # Check sampling rate
    if not evaluator.should_sample():
        logger.debug("Skipping evaluation (sample rate)")
        return

    try:
        results = await evaluator.evaluate_async(
            input_text=user_input,
            output_text=response_text,
        )
        for result in results:
            logger.info(
                "Eval [trace=%s] %s: %s (score=%.2f)",
                trace_id or "no-trace",
                result.evaluator_name,
                result.label,
                result.score or 0.0,
            )
    except Exception:
        logger.exception("Online evaluation failed for trace %s", trace_id)


def _normalize_event(event: Any) -> dict[str, Any] | None:
    """Normalize event from single-agent or multi-agent format.

    Multi-agent events are passed through as-is so StreamState can handle them.
    For multiagent_node_stream, we pass the whole event (not just inner) so
    StreamState can track which agent is producing the output.
    """
    if not isinstance(event, dict):
        return None
    # Pass multi-agent events through for StreamState to handle
    event_type = event.get("type")
    if event_type in (
        "multiagent_node_start",
        "multiagent_node_stop",
        "multiagent_handoff",
        "multiagent_node_stream",
    ):
        return event
    return event


def _encode_rich_chunk(
    content: list[ContentPart],
    trace_id: str | None = None,
    session_id: str | None = None,
    run_mode: str | None = None,
    profile_name: str | None = None,
    model_id: str | None = None,
    execution_mode: str | None = None,
    entrypoint_reference: str | None = None,
) -> bytes:
    """Encode a rich content chunk with tool calls and reasoning."""
    chunk = RichStreamChunk(
        content=content,
        phoenixTraceId=trace_id,
        phoenixSessionId=session_id,
        runMode=run_mode,
        profileName=profile_name,
        modelId=model_id,
        executionMode=execution_mode,
        entrypointReference=entrypoint_reference,
    )
    return (chunk.model_dump_json(by_alias=True, exclude_none=True) + "\n").encode()


def _convert_to_strands_messages(
    messages: list,
    compact_tools: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Convert assistant-ui messages to Strands SDK message format."""
    strands_messages: list[dict[str, Any]] = []
    stats: dict[str, Any] = {
        "message_count": 0,
        "tool_calls_stripped": 0,
        "tool_results_kept": 0,
        "tool_calls_by_name": {},
    }

    for msg in messages:
        if msg.role not in ("user", "assistant"):
            continue

        content_blocks: list[dict[str, Any]] = []
        for part in msg.content:
            part_type = part.get("type")

            if part_type == "text":
                text = part.get("text", "")
                if text:
                    content_blocks.append({"text": text})
            elif part_type == "tool-call":
                block = _convert_tool_call_part(part, compact_tools, stats)
                if block:
                    content_blocks.append(block)
            elif part_type == "tool-result":
                content_blocks.append(_convert_tool_result_part(part, compact_tools, stats))

        if content_blocks:
            strands_messages.append({"role": msg.role, "content": content_blocks})
            stats["message_count"] += 1

    return strands_messages, stats


def _convert_tool_call_part(
    part: dict[str, Any], compact: bool, stats: dict[str, Any]
) -> dict[str, Any] | None:
    """Convert a tool-call content part to Strands format."""
    tool_name = part.get("toolName", "")
    stats["tool_calls_by_name"][tool_name] = stats["tool_calls_by_name"].get(tool_name, 0) + 1

    if compact:
        stats["tool_calls_stripped"] += 1
        return None
    return {
        "toolUse": {
            "toolUseId": part.get("toolCallId", ""),
            "name": tool_name,
            "input": part.get("args", {}),
        }
    }


def _convert_tool_result_part(
    part: dict[str, Any], compact: bool, stats: dict[str, Any]
) -> dict[str, Any]:
    """Convert a tool-result content part to Strands format."""
    result_content = part.get("result")
    stats["tool_results_kept"] += 1

    if compact:
        preview = str(result_content)[:200] if result_content else "No result"
        if len(str(result_content)) > 200:
            preview += "..."
        return {"text": f"[Tool result: {preview}]"}
    return {
        "toolResult": {
            "toolUseId": part.get("toolCallId", ""),
            "content": [{"text": str(result_content)}] if result_content else [],
            "status": "error" if part.get("isError") else "success",
        }
    }
