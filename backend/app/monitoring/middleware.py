"""FastAPI middleware for monitoring and observability."""

import time
import uuid
from typing import Callable, Optional
from functools import wraps

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.monitoring.metrics import (
    record_http_request,
    http_requests_in_flight,
    update_infrastructure_metrics,
)
from app.monitoring.tracing import (
    tracer,
    inject_trace_context,
    extract_trace_context,
    trace_operation,
)
from app.monitoring.logging import (
    set_request_context,
    clear_request_context,
    get_request_context,
    log_request,
)
from app.monitoring.tracing import tracer as tracing_tracer
from app.core.logging import get_logger
from app.core.config import get_settings

settings = get_settings()
logger = get_logger(__name__)


class MonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for request monitoring, tracing, and metrics."""

    def __init__(
        self,
        app: ASGIApp,
        excluded_paths: Optional[list] = None,
    ):
        super().__init__(app)
        self.excluded_paths = excluded_paths or ["/health", "/metrics", "/favicon.ico", "/docs", "/openapi.json", "/redoc"]
        self._start_time = time.time()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip monitoring for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Generate request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Extract trace context from headers
        trace_context = {}
        trace_header = request.headers.get("X-Trace-ID") or request.headers.get("x-trace-id")
        span_header = request.headers.get("X-Span-ID") or request.headers.get("x-span-id")
        parent_span_header = request.headers.get("X-Parent-Span-ID") or request.headers.get("x-parent-span-id")

        if trace_header:
            trace_context = {
                "trace_id": trace_header,
                "span_id": span_header or "",
                "parent_span_id": parent_span_header,
            }

        # Start tracing
        from app.monitoring.tracing import tracer
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()).replace("-", ""))
        span_id = str(uuid.uuid4()).replace("-", "")[:16]

        # Start span for this request using context manager
        span_cm = trace_operation(
            operation_name=f"HTTP {request.method}",
            tags={
                "http.method": request.method,
                "http.url": str(request.url),
                "http.route": request.url.path,
                "component": "http-server",
            },
        )
        # Get the span from the context manager
        span = span_cm.__enter__()

        # Add trace context to request state
        request.state.trace_id = span.trace_id
        request.state.span_id = span.span_id
        request.state.request_id = request_id

        # Set request context for logging
        request_context = {
            "request_id": request.headers.get("X-Request-ID", str(uuid.uuid4())),
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "method": request.method,
            "path": request.url.path,
            "start_time": time.time(),
        }
        # Note: We can't use contextvar here as it's not async-safe in middleware
        # Store in request state instead
        request.state.log_context = {
            "request_id": request_id,
            "trace_id": span.trace_id,
            "span_id": span.span_id,
            "method": request.method,
            "path": str(request.url.path),
            "start_time": time.time(),
        }

        # Track in-flight requests
        endpoint_normalized = self._normalize_endpoint(request.url.path)
        http_requests_in_flight.labels(
            method=request.method,
            endpoint=self._normalize_endpoint(request.url.path)
        ).inc()

        start_time = time.perf_counter()
        request_size = 0
        response_size = 0

        try:
            # Read request body size
            if hasattr(request, "body"):
                try:
                    body = await request.body()
                    request_size = len(body)
                except:
                    pass

            # Process request
            response = await call_next(request)

            # Calculate response size
            if hasattr(response, "headers"):
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        response_size = int(content_length)
                    except:
                        pass

            duration = time.perf_counter() - start_time

            # Record metrics
            record_http_request(
                method=request.method,
                endpoint=self._normalize_endpoint(request.url.path),
                status_code=response.status_code,
                duration_seconds=duration,
                request_size=request_size,
                response_size=response_size,
            )

            # Add trace headers to response
            current_span = tracing_tracer.get_current_span()
            if current_span:
                response.headers["X-Trace-ID"] = current_span.trace_id
                response.headers["X-Span-ID"] = current_span.span_id
            response.headers["X-Request-ID"] = request.headers.get("X-Request-ID", str(uuid.uuid4()))

            # Add timing headers
            response.headers["X-Response-Time"] = f"{duration * 1000:.2f}ms"

            # Log request
            log_request(
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                duration_ms=duration * 1000,
                request_id=request.headers.get("X-Request-ID", str(uuid.uuid4())),
            )

            # Close the span context manager
            span_cm.__exit__(None, None, None)

            return response

        except Exception as e:
            # Record error metrics
            duration = time.perf_counter() - start_time
            record_http_request(
                method=request.method,
                endpoint=self._normalize_endpoint(request.url.path),
                status_code=500,
                duration_seconds=duration,
            )
            logger.error(f"Request failed: {request.method} {request.url.path}", exc_info=True)
            # Close the span context manager with error
            span_cm.__exit__(type(e), e, e.__traceback__)
            raise
        finally:
            # Decrement in-flight counter
            http_requests_in_flight.labels(
                method=request.method,
                endpoint=self._normalize_endpoint(request.url.path)
            ).dec()

    def _normalize_endpoint(self, path: str) -> str:
        """Normalize endpoint path for metrics grouping."""
        import re
        path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/:uuid', path)
        path = re.sub(r'/\d+', '/:id', path)
        # Limit path length
        if len(path) > 100:
            path = path[:100] + "..."
        return path


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for distributed tracing."""

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract trace context from headers
        trace_context = extract_trace_context(dict(request.headers))

        # Set trace context for this request
        if trace_context:
            from app.monitoring.tracing import _trace_context, TraceContext
            ctx = TraceContext(
                trace_id=trace_context.get("trace_id", ""),
                span_id=trace_context.get("span_id", ""),
                parent_span_id=trace_context.get("parent_span_id"),
                sampled=trace_context.get("sampled", True),
            )
            _trace_context.set(ctx)

        # Add trace context to request state for downstream use
        request.state.trace_context = extract_trace_context(dict(request.headers))

        return await call_next(request)


def get_route_path(request: Request) -> str:
    """Get the route path template for metrics grouping."""
    route = request.scope.get("route")
    if route and hasattr(route, "path"):
        return route.path
    return request.url.path


def create_monitoring_middleware(app: ASGIApp) -> ASGIApp:
    """Create monitoring middleware stack."""
    # Apply middlewares in order (outermost first)
    app = MonitoringMiddleware(app)
    app = TracingMiddleware(app)
    return app