"""Chat streaming orchestration service."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from agent_toolkit.config.execution_mode import get_execution_mode_resolver
from agent_toolkit.telemetry import EvalConfig, OnlineEvaluator

from assistant_web_backend.models.messages import ContentPart, MessagePayload, RichStreamChunk
from assistant_web_backend.services.message_codec import convert_to_strands_messages
from assistant_web_backend.services.runtime import get_runtime
from assistant_web_backend.services.settings import get_settings
from assistant_web_backend.services.streaming import StreamState

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from assistant_web_backend.models.threads import ChatRunRequest
    from assistant_web_backend.storage import Storage

logger = logging.getLogger(__name__)

_online_evaluator: OnlineEvaluator | None = None
_background_tasks: set[asyncio.Task[None]] = set()


def _get_evaluator() -> OnlineEvaluator:
    """Get or create the online evaluator singleton."""
    global _online_evaluator  # noqa: PLW0603
    if _online_evaluator is None:
        settings = get_settings()
        config = EvalConfig.from_settings(settings)
        _online_evaluator = OnlineEvaluator(config)
    return _online_evaluator


def _schedule_background_task(coro: Any) -> None:
    """Schedule a background task and track it to prevent GC."""
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


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


def _format_agent_error(exc: Exception) -> str:
    """Return a user-friendly error message for known provider failures."""
    message = str(exc)
    if "inference profile" in message.lower() or "on-demand throughput isn" in message.lower():
        return (
            "Agent error: This model requires an inference profile for on-demand throughput. "
            "Select an inference profile from the Model override dropdown and retry."
        )
    return f"Agent error: {message}"


def _encode_rich_chunk(
    content: list[ContentPart],
    *,
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


def _resolve_run_mode(payload: ChatRunRequest, resolver, settings) -> str:
    run_mode = payload.run_mode or resolver.get_default_profile() or settings.run_mode
    if not run_mode:
        msg = "No public profiles configured; run_mode is required"
        raise RuntimeError(msg)
    return run_mode


def _resolve_execution_metadata(resolver, run_mode: str) -> tuple[str, str]:
    try:
        execution_mode, entrypoint_reference, _resolved_metadata = resolver.resolve_execution_mode(
            run_mode
        )
        return execution_mode, entrypoint_reference
    except (RuntimeError, ValueError):
        logger.exception("Failed to resolve execution mode for profile '%s'", run_mode)
        raise


def _select_model_id(
    execution_mode: str,
    entrypoint_reference: str,
    profiles: list[Any],
    settings,
) -> str | None:
    if execution_mode != "single":
        return None
    profile = next((p for p in profiles if p.name == entrypoint_reference), None)
    return profile.model if profile and profile.model else settings.bedrock_model_id


def _extract_user_input(messages: list[MessagePayload]) -> str:
    for msg in messages:
        if msg.role == "user":
            for part in msg.content:
                if part.get("type") == "text":
                    return part.get("text", "")
    return ""


def _build_invocation_state(
    runtime, thread_id: str, run_mode: str, message_id: str
) -> dict[str, str]:
    return runtime.build_invocation_state(
        "",
        thread_id or f"thread-{run_mode}",
        thread_id=thread_id or "",
        message_id=message_id,
        run_mode=run_mode,
        profile_name=run_mode,
    )


async def stream_chat(
    thread_id: str,
    payload: ChatRunRequest,
    storage: Storage,
) -> AsyncGenerator[bytes]:
    """Run the agent stream and yield encoded chunks."""
    runtime = get_runtime()
    settings = get_settings()
    profiles = runtime.list_profiles()

    resolver = get_execution_mode_resolver()
    run_mode = _resolve_run_mode(payload, resolver, settings)

    try:
        execution_mode, entrypoint_reference = _resolve_execution_metadata(resolver, run_mode)
    except (RuntimeError, ValueError) as exc:
        yield _encode_rich_chunk(
            [ContentPart(type="text", text=_format_agent_error(exc))],
            run_mode=run_mode,
        )
        return

    model_id = _select_model_id(execution_mode, entrypoint_reference, profiles, settings)

    state = StreamState()
    captured_trace_id: str | None = None
    user_input = _extract_user_input(payload.messages)

    strands_messages, conversion_stats = convert_to_strands_messages(
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

    if thread_id:
        storage.create_thread(thread_id)

    invocation_state = _build_invocation_state(runtime, thread_id, run_mode, message_id)

    try:
        async for event in runtime.stream(
            mode=run_mode,
            profile_name=run_mode,
            messages=strands_messages,
            invocation_state=invocation_state,
            session_id=thread_id or f"thread-{run_mode}",
        ):
            trace_id_from_event = _extract_phoenix_metadata(event)
            if trace_id_from_event:
                captured_trace_id = trace_id_from_event
                logger.debug("Captured Phoenix trace_id from event: %s", captured_trace_id)

            if isinstance(event, dict) and event.get("type") == "stream_metadata":
                continue

            event_data = state.normalize_event(event)
            if event_data and state.handle_event(event_data):
                yield _encode_rich_chunk(
                    state.build_content(),
                    trace_id=captured_trace_id or None,
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

        response_text = state.get_text_content()
        if response_text and user_input:
            _schedule_background_task(_run_evaluation(user_input, response_text, captured_trace_id))
    except Exception as exc:
        logger.exception("Agent stream failed")
        yield _encode_rich_chunk([ContentPart(type="text", text=_format_agent_error(exc))])


async def _run_evaluation(
    user_input: str,
    response_text: str,
    trace_id: str | None,
) -> None:
    """Run online evaluation in background."""
    evaluator = _get_evaluator()
    if not evaluator.enabled:
        return

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
