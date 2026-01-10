"""Distributed tracing support."""

import uuid
from contextvars import ContextVar
from typing import Any

import structlog

# Context variable for trace ID
_trace_id: ContextVar[str] = ContextVar("trace_id", default="")


def generate_trace_id() -> str:
    """Generate a new trace ID."""
    return uuid.uuid4().hex[:16]


def get_trace_id() -> str:
    """Get current trace ID."""
    return _trace_id.get() or generate_trace_id()


def set_trace_id(trace_id: str) -> None:
    """Set current trace ID."""
    _trace_id.set(trace_id)
    # Also bind to structlog context
    structlog.contextvars.bind_contextvars(trace_id=trace_id)


def clear_trace_id() -> None:
    """Clear current trace ID."""
    _trace_id.set("")
    structlog.contextvars.unbind_contextvars("trace_id")


class TraceContext:
    """Context manager for trace ID."""

    def __init__(self, trace_id: str | None = None):
        """Initialize with optional trace ID."""
        self._trace_id = trace_id or generate_trace_id()
        self._previous_id: str = ""

    def __enter__(self) -> str:
        """Enter context and set trace ID."""
        self._previous_id = get_trace_id()
        set_trace_id(self._trace_id)
        return self._trace_id

    def __exit__(self, *args: Any) -> None:
        """Exit context and restore previous trace ID."""
        if self._previous_id:
            set_trace_id(self._previous_id)
        else:
            clear_trace_id()
