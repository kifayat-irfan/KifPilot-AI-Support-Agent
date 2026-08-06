"""Structured logging for KifPilot."""

import json
import logging
import sys
import traceback
from typing import Optional, Dict, Any, Any
from datetime import datetime
from contextvars import ContextVar
from dataclasses import dataclass, field, asdict
from typing import Any
from pythonjsonlogger import jsonlogger

from app.monitoring.schemas import LogEntry
from app.monitoring.tracing import get_current_trace_context
from app.core.config import get_settings
from app.core.logging import get_logger as get_core_logger

settings = get_settings()

# Context variables for request context
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_context', default=None)


@dataclass
class RequestContext:
    """Request context for logging."""
    request_id: str = ""
    trace_id: str = ""
    span_id: str = ""
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    session_id: Optional[str] = None
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    start_time: float = 0.0


# Global context variable
_request_context_var: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_context', default=None)


class StructuredJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter for structured logging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.json_encoder = json.dumps

    def add_fields(self, log_record: Dict[str, Any], record: logging.LogRecord, message_dict: Dict[str, Any]) -> None:
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = datetime.utcnow().isoformat() + "Z"
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["function"] = record.funcName
        log_record["line"] = record.lineno

        # Add request context if available
        request_ctx = _request_context_var.get()
        if request_ctx:
            log_record["request_id"] = request_ctx.get("request_id")
            log_record["trace_id"] = request_ctx.get("trace_id")
            log_record["span_id"] = request_ctx.get("span_id")
            log_record["user_id"] = request_ctx.get("user_id")
            log_record["organization_id"] = request_ctx.get("organization_id")
            log_record["session_id"] = request_ctx.get("session_id")
            log_record["method"] = request_ctx.get("method")
            log_record["path"] = request_ctx.get("path")
            log_record["status_code"] = request_ctx.get("status_code")
            if request_ctx.get("start_time"):
                log_record["duration_ms"] = (time.time() - request_ctx["start_time"]) * 1000

        # Add trace context if available
        trace_ctx = get_current_trace_context()
        if trace_ctx:
            log_record["trace_id"] = trace_ctx.get("trace_id")
            log_record["span_id"] = trace_ctx.get("span_id")

        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_record.update(record.extra_fields)

    def formatException(self, exc_info):
        """Format exception with traceback."""
        return "".join(traceback.format_exception(*exc_info))

    def formatStack(self, stack_info):
        """Format stack info."""
        return "".join(traceback.format_stack())


class StructuredLogger:
    """Structured logger with context support."""

    def __init__(self, name: str, level: int = logging.INFO):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self._configure_handler()

    def _configure_handler(self):
        """Configure JSON handler."""
        # Remove existing handlers
        self.logger.handlers.clear()

        # Create handler
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.logger.level)

        # Create formatter
        formatter = StructuredJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)

        # Prevent propagation to root logger
        self.logger.propagate = False

    def _log(self, level: int, message: str, **kwargs):
        """Log with extra fields."""
        extra = {"extra_fields": kwargs} if kwargs else {}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)

    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with traceback."""
        self.logger.exception(message, extra={"extra_fields": kwargs})

    def log(self, level: int, message: str, **kwargs):
        """Log at specified level."""
        self._log(level, message, **kwargs)


class RequestLogger:
    """Logger for HTTP requests with context."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger

    def log_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
        request_id: str = "",
        trace_id: str = "",
        span_id: str = "",
        user_id: str = "",
        organization_id: str = "",
        session_id: str = "",
        request_size: int = 0,
        response_size: int = 0,
    ):
        """Log HTTP request."""
        self.logger.info(
            f"{method} {path} {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=duration_ms,
            request_id=request_id,
            trace_id=trace_id,
            span_id=span_id,
            user_id=user_id,
            organization_id=organization_id,
            session_id=session_id,
            request_size=request_size,
            response_size=response_size,
            event_type="http_request",
        )

    def log_error(
        self,
        method: str,
        path: str,
        error: Exception,
        request_id: str = "",
        trace_id: str = "",
        span_id: str = "",
        user_id: str = "",
        organization_id: str = "",
    ):
        """Log request error."""
        self.logger.error(
            f"Request failed: {method} {path}",
            method=method,
            path=path,
            error_type=type(error).__name__,
            error_message=str(error),
            request_id=request_id,
            trace_id=trace_id,
            span_id=span_id,
            user_id=user_id,
            organization_id=organization_id,
            event_type="http_error",
        )


def set_request_context(context: Dict[str, Any]):
    """Set request context for logging."""
    _request_context_var.set(context)


def clear_request_context():
    """Clear request context."""
    _request_context_var.set(None)


def get_request_context() -> Optional[Dict[str, Any]]:
    """Get current request context."""
    return _request_context_var.get()


class LoggerMixin:
    """Mixin to add structured logging to a class."""

    @property
    def logger(self) -> StructuredLogger:
        if not hasattr(self, "_logger"):
            self._logger = StructuredLogger(self.__class__.__name__)
        return self._logger

    def log_info(self, message: str, **kwargs):
        self.logger.info(message, **kwargs)

    def log_debug(self, message: str, **kwargs):
        self.logger.debug(message, **kwargs)

    def log_warning(self, message: str, **kwargs):
        self.logger.warning(message, **kwargs)

    def log_error(self, message: str, **kwargs):
        self.logger.error(message, **kwargs)

    def log_critical(self, message: str, **kwargs):
        self.logger.critical(message, **kwargs)

    def log_exception(self, message: str, **kwargs):
        self.logger.exception(message, **kwargs)


# Global logger instances
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """Get or create a structured logger."""
    if name not in _loggers:
        level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        _loggers[name] = StructuredLogger(name, level)
    return _loggers[name]


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """Setup application-wide logging."""
    level = getattr(logging, level.upper(), logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    
    if json_format and settings.LOG_FORMAT == "json":
        formatter = StructuredJsonFormatter(
            "%(timestamp)s %(level)s %(logger)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Set levels for third-party loggers
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    
    logger.info("Logging configured", level=level, json_format=json_format)


# Context manager for request logging
class RequestLoggingContext:
    """Context manager for request logging."""

    def __init__(
        self,
        request_id: str,
        trace_id: str = "",
        span_id: str = "",
        user_id: str = "",
        organization_id: str = "",
        session_id: str = "",
        method: str = "",
        path: str = "",
    ):
        self.context = {
            "request_id": request_id,
            "trace_id": trace_id,
            "span_id": span_id,
            "user_id": user_id,
            "organization_id": organization_id,
            "session_id": session_id,
            "method": method,
            "path": path,
            "start_time": time.time(),
        }

    def __enter__(self):
        set_request_context(self.context)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        clear_request_context()

    def set_status_code(self, status_code: int):
        """Set response status code."""
        self.context["status_code"] = status_code

    def set_user(self, user_id: str, organization_id: str = ""):
        """Set user context."""
        self.context["user_id"] = user_id
        if organization_id:
            self.context["organization_id"] = organization_id


# Convenience function for request logging
def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    **kwargs
):
    """Log HTTP request."""
    logger = get_logger("http")
    logger.info(
        f"{method} {path} {status_code}",
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        event_type="http_request",
        **kwargs
    )


def log_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
    **kwargs
):
    """Log error with context."""
    logger = get_logger("error")
    logger.error(
        f"Error: {type(error).__name__}: {error}",
        error_type=type(error).__name__,
        error_message=str(error),
        traceback=traceback.format_exc(),
        context=context or {},
        **kwargs
    )