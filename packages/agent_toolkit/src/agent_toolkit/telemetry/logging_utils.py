"""Logging helpers for trace correlation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from agent_toolkit.telemetry.phoenix import get_current_trace_id

if TYPE_CHECKING:
    from collections.abc import Iterable


class TraceContextFilter(logging.Filter):
    """Attach trace identifiers to log records when available."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Inject trace_id into the log record."""
        record.trace_id = get_current_trace_id() or "-"
        return True


def install_trace_log_filter(loggers: Iterable[logging.Logger] | None = None) -> None:
    """Install trace context filters for structured logging.

    Args:
        loggers: Optional iterable of loggers to attach the filter to. Defaults to root logger.
    """
    targets = list(loggers) if loggers is not None else [logging.getLogger()]
    for logger in targets:
        if any(isinstance(flt, TraceContextFilter) for flt in logger.filters):
            continue
        logger.addFilter(TraceContextFilter())
