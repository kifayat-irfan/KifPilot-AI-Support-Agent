"""Distributed tracing for KifPilot."""

import time
import uuid
import contextvars
from contextlib import contextmanager
from typing import Optional, Dict, Any, List, Callable, Any
from functools import wraps
from datetime import datetime
from dataclasses import dataclass, field
from contextlib import asynccontextmanager
import logging

from app.monitoring.schemas import (
    TraceContext, SpanData
)
from app.core.logging import get_logger

logger = get_logger(__name__)

# Context variables for trace propagation
_trace_context: contextvars.ContextVar[Optional['TraceContext']] = contextvars.ContextVar('trace_context', default=None)
_current_span: contextvars.ContextVar[Optional['Span']] = contextvars.ContextVar('current_span', default=None)


@dataclass
class Span:
    """Active span for distributed tracing."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation_name: str = ""
    service_name: str = "kifpilot"
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    tags: Dict[str, str] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"
    error_message: Optional[str] = None

    @property
    def span_id_short(self) -> str:
        return self.span_id[:8]

    @property
    def trace_id_short(self) -> str:
        return self.trace_id[:8]

    def finish(self, status: str = "ok", error_message: Optional[str] = None):
        """Finish the span."""
        self.end_time = time.perf_counter()
        self.status = status
        if error_message:
            self.error_message = error_message
            self.status = "error"

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.perf_counter()
        return (self.end_time or time.perf_counter()) - self.start_time * 1000

    def to_span_data(self) -> dict:
        """Convert to SpanData schema."""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "operation_name": self.operation_name,
            "service_name": self.service_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat() if self.start_time else None,
            "end_time": datetime.fromtimestamp(self.end_time).isoformat() if self.end_time else None,
            "duration_ms": (self.end_time - self.start_time) * 1000 if self.end_time else None,
            "tags": self.tags,
            "logs": self.logs,
            "status": self.status,
            "error_message": self.error_message,
        }

    def add_tag(self, key: str, value: str):
        """Add a tag to the span."""
        self.tags[key] = value

    def add_log(self, message: str, level: str = "info", fields: Optional[Dict[str, Any]] = None):
        """Add a log entry to the span."""
        self.logs.append({
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
            "fields": fields or {},
        })

    def set_error(self, error: Exception):
        """Mark span as error with exception info."""
        self.status = "error"
        self.error_message = str(error)
        self.add_tag("error.type", type(error).__name__)
        self.add_log(f"Error: {error}", level="error", fields={"exception": str(error)})


class Tracer:
    """Distributed tracer for generating and managing spans."""

    def __init__(self, service_name: str = "kifpilot"):
        self.service_name = service_name
        self._spans: Dict[str, Span] = {}
        self._span_stack: List[Span] = []

    def start_span(
        self,
        operation_name: str,
        parent_span: Optional[Span] = None,
        tags: Optional[Dict[str, str]] = None,
        service_name: Optional[str] = None,
    ) -> Span:
        """Start a new span."""
        # Generate IDs
        trace_id = parent_span.trace_id if parent_span else str(uuid.uuid4()).replace("-", "")
        span_id = str(uuid.uuid4()).replace("-", "")
        parent_span_id = parent_span.span_id if parent_span else None

        # Create span
        span = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            operation_name=operation_name,
            service_name=service_name or self.service_name,
            tags=tags or {},
        )

        # Store span
        self._spans[span.span_id] = span
        self._span_stack.append(span)

        # Set as current span
        _current_span.set(span)

        # Propagate trace context
        trace_ctx = TraceContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            sampled=True,
        )
        _trace_context.set(trace_ctx)

        logger.debug(
            f"Started span: {operation_name}",
            extra={
                "trace_id": trace_id[:8],
                "span_id": span_id[:8],
                "parent_span_id": parent_span_id[:8] if parent_span_id else None,
            }
        )

        return span

    def get_current_span(self) -> Optional[Span]:
        """Get the currently active span."""
        return _current_span.get()

    def get_trace_context(self) -> Optional[TraceContext]:
        """Get the current trace context."""
        return _trace_context.get()

    def finish_span(self, span: Span, status: str = "ok", error_message: Optional[str] = None):
        """Finish a span."""
        span.finish(status, error_message)
        
        # Remove from stack
        if self._span_stack and self._span_stack[-1] == span:
            self._span_stack.pop()
        
        # Update current span
        if self._span_stack:
            _current_span.set(self._span_stack[-1])
        else:
            _current_span.set(None)
            _trace_context.set(None)

        logger.debug(
            f"Finished span: {span.operation_name}",
            extra={
                "trace_id": span.trace_id[:8],
                "span_id": span.span_id[:8],
                "duration_ms": span.duration_ms,
                "status": span.status,
            }
        )

    def get_span(self, span_id: str) -> Optional[Span]:
        """Get a span by ID."""
        return self._spans.get(span_id)

    def get_trace_spans(self, trace_id: str) -> List[Span]:
        """Get all spans for a trace."""
        return [s for s in self._spans.values() if s.trace_id == trace_id]

    def export_spans(self) -> List[dict]:
        """Export all spans as dictionaries."""
        return [s.to_span_data() for s in self._spans.values()]


# Global tracer instance
tracer = Tracer()


def get_tracer() -> Tracer:
    """Get the global tracer instance."""
    return tracer


# ============================================================================
# Decorators and Context Managers
# ============================================================================

def trace(
    operation_name: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None,
    service_name: Optional[str] = None,
):
    """Decorator to trace a function."""
    def decorator(func: Callable) -> Callable:
        op_name = operation_name or f"{func.__module__}.{func.__qualname__}"

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            span = tracer.start_span(
                operation_name=op_name,
                tags=tags,
                service_name=service_name,
            )
            try:
                result = func(*args, **kwargs)
                tracer.finish_span(span, "ok")
                return result
            except Exception as e:
                tracer.finish_span(span, "error", str(e))
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            span = tracer.start_span(
                operation_name=op_name,
                tags=tags,
                service_name=service_name,
            )
            try:
                result = await func(*args, **kwargs)
                tracer.finish_span(span, "ok")
                return result
            except Exception as e:
                tracer.finish_span(span, "error", str(e))
                raise

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


@contextmanager
def trace_operation(
    operation_name: str,
    tags: Optional[Dict[str, str]] = None,
    service_name: Optional[str] = None,
):
    """Context manager for tracing an operation."""
    span = tracer.start_span(operation_name, tags=tags, service_name=service_name)
    try:
        yield span
        tracer.finish_span(span, "ok")
    except Exception as e:
        tracer.finish_span(span, "error", str(e))
        raise


@asynccontextmanager
async def atrace_operation(
    operation_name: str,
    tags: Optional[Dict[str, str]] = None,
    service_name: Optional[str] = None,
):
    """Async context manager for tracing an operation."""
    span = tracer.start_span(operation_name, tags=tags, service_name=service_name)
    try:
        yield span
        tracer.finish_span(span, "ok")
    except Exception as e:
        tracer.finish_span(span, "error", str(e))
        raise


def get_current_trace_context() -> Optional[Dict[str, str]]:
    """Get current trace context for propagation."""
    ctx = _trace_context.get()
    if ctx:
        return {
            "trace_id": ctx.trace_id,
            "span_id": ctx.span_id,
            "parent_span_id": ctx.parent_span_id or "",
        }
    return None


def inject_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """Inject trace context into headers for propagation."""
    ctx = get_current_trace_context()
    if ctx:
        headers["X-Trace-ID"] = ctx["trace_id"]
        headers["X-Span-ID"] = ctx["span_id"]
        if ctx["parent_span_id"]:
            headers["X-Parent-Span-ID"] = ctx["parent_span_id"]
    return headers


def extract_trace_context(headers: Dict[str, str]) -> Optional[Dict[str, str]]:
    """Extract trace context from headers."""
    trace_id = headers.get("X-Trace-ID") or headers.get("x-trace-id")
    span_id = headers.get("X-Span-ID") or headers.get("x-span-id")
    parent_span_id = headers.get("X-Parent-Span-ID") or headers.get("x-parent-span-id")

    if trace_id and span_id:
        return {
            "trace_id": trace_id,
            "span_id": span_id,
            "parent_span_id": parent_span_id,
        }
    return None


# ============================================================================
# Integration with HTTP and async operations
# ============================================================================

class TracedHTTPClient:
    """HTTP client with automatic tracing."""

    def __init__(self, client, tracer: Tracer = None):
        self.client = client
        self.tracer = tracer or tracer

    async def request(self, method: str, url: str, **kwargs) -> Any:
        # Extract trace context from kwargs if present
        headers = kwargs.pop("headers", {})
        trace_ctx = extract_trace_context(headers) if headers else None

        # Start span
        span = self.tracer.start_span(
            operation_name=f"HTTP {method}",
            tags={
                "http.method": method,
                "http.url": url,
                "component": "http-client",
            },
        )

        if trace_ctx:
            # Continue existing trace
            pass  # Parent context already set via contextvars

        # Inject trace context into outgoing headers
        headers = inject_trace_context(headers)

        start_time = time.perf_counter()
        try:
            response = await self.client.request(method, url, headers=headers, **kwargs)
            self.tracer.finish_span(span, "ok")
            return response
        except Exception as e:
            self.tracer.finish_span(span, "error", str(e))
            raise


def trace_database_operation(operation: str, table: str = ""):
    """Decorator to trace database operations."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            span = tracer.start_span(
                operation_name=f"db.{operation}",
                tags={
                    "db.operation": operation,
                    "db.table": table,
                    "component": "database",
                },
            )
            try:
                result = func(*args, **kwargs)
                tracer.finish_span(span, "ok")
                return result
            except Exception as e:
                tracer.finish_span(span, "error", str(e))
                raise

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            span = tracer.start_span(
                operation_name=f"db.{operation}",
                tags={
                    "db.operation": operation,
                    "db.table": table,
                    "component": "database",
                },
            )
            try:
                result = await func(*args, **kwargs)
                tracer.finish_span(span, "ok")
                return result
            except Exception as e:
                tracer.finish_span(span, "error", str(e))
                raise

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


# Global trace context for async propagation
def set_trace_context(ctx: Dict[str, str]):
    """Set trace context for current execution context."""
    trace_ctx = TraceContext(
        trace_id=ctx.get("trace_id", ""),
        span_id=ctx.get("span_id", ""),
        parent_span_id=ctx.get("parent_span_id"),
        sampled=ctx.get("sampled", True),
    )
    _trace_context.set(trace_ctx)


def clear_trace_context():
    """Clear trace context."""
    _trace_context.set(None)
    _current_span.set(None)