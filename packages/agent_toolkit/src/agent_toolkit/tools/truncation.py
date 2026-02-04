"""Tool output truncation utilities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TruncationResult:
    """Result of truncating a tool output."""

    text: str
    truncated: bool
    original_length: int
    truncated_length: int


def truncate_text(text: str, max_chars: int, suffix: str = "...") -> TruncationResult:
    """Truncate text to a maximum number of characters."""
    original_length = len(text)
    if max_chars <= 0:
        return TruncationResult(
            text="",
            truncated=original_length > 0,
            original_length=original_length,
            truncated_length=0,
        )
    if original_length <= max_chars:
        return TruncationResult(
            text=text,
            truncated=False,
            original_length=original_length,
            truncated_length=original_length,
        )

    if len(suffix) >= max_chars:
        truncated_text = suffix[:max_chars]
        return TruncationResult(
            text=truncated_text,
            truncated=True,
            original_length=original_length,
            truncated_length=len(truncated_text),
        )

    cut = max_chars - len(suffix)
    truncated_text = f"{text[:cut]}{suffix}"
    return TruncationResult(
        text=truncated_text,
        truncated=True,
        original_length=original_length,
        truncated_length=len(truncated_text),
    )


def truncate_lines(text: str, max_lines: int, suffix: str = "...") -> TruncationResult:
    """Truncate text to a maximum number of lines."""
    lines = text.splitlines()
    original_length = len(text)
    if max_lines <= 0:
        return TruncationResult(
            text="",
            truncated=original_length > 0,
            original_length=original_length,
            truncated_length=0,
        )
    if len(lines) <= max_lines:
        return TruncationResult(
            text=text,
            truncated=False,
            original_length=original_length,
            truncated_length=original_length,
        )

    truncated_text = "\n".join(lines[:max_lines])
    if suffix:
        truncated_text = f"{truncated_text}\n{suffix}"
    return TruncationResult(
        text=truncated_text,
        truncated=True,
        original_length=original_length,
        truncated_length=len(truncated_text),
    )
