"""Security middleware for KifPilot."""

import time
import uuid
from typing import Optional, Callable, Dict, Any, Set
from dataclasses import dataclass, field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
from starlette.types import ASGIApp

from app.security.rate_limiter import get_rate_limiter, rate_limit_dependency
from app.security.audit import get_audit_logger, set_audit_context, clear_audit_context, AuditEventType
from app.security.validation import get_input_validator, InputValidator
from app.security.upload_security import get_upload_validator
from app.security.headers import SecurityHeadersMiddleware
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class SecurityMiddlewareConfig:
    """Configuration for security middleware."""
    # Rate limiting
    enable_rate_limiting: bool = True
    
    # Audit logging
    enable_audit_logging: bool = True
    
    # Input validation
    enable_input_validation: bool = True
    validate_headers: bool = True
    validate_query: bool = True
    validate_body: bool = True
    
    # Security headers
    enable_security_headers: bool = True
    
    # Abuse protection
    enable_abuse_protection: bool = True
    max_request_size: int = 10 * 1024 * 1024  # 10 MB
    max_streaming_tokens: int = 4096
    failed_login_threshold: int = 5
    failed_login_window_minutes: int = 15
    
    # Exempt paths
    exempt_paths: Set[str] = field(default_factory=lambda: {
        "/",
        "/health",
        "/health/",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico",
    })


def get_security_middleware_config() -> SecurityMiddlewareConfig:
    """Get security middleware configuration."""
    config = SecurityMiddlewareConfig()
    
    if settings.DEBUG:
        config.enable_rate_limiting = False
        config.enable_input_validation = False
        config.enable_security_headers = False
        config.enable_abuse_protection = False
    
    return config


class AbuseProtectionMiddleware(BaseHTTPMiddleware):
    """Middleware for abuse protection."""
    
    def __init__(self, app: ASGIApp, config: Optional[SecurityMiddlewareConfig] = None):
        super().__init__(app)
        self.config = config or get_security_middleware_config()
        self._failed_logins: Dict[str, list] = {}
        self._request_counts: Dict[str, list] = {}
        self._cleanup_task = None
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.config.enable_abuse_protection:
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        
        # Check request size
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > self.config.max_request_size:
            logger.warning("Request too large", ip=client_ip, size=content_length)
            return JSONResponse(
                status_code=413,
                content={"detail": "Request entity too large"},
            )
        
        # Track failed logins
        if request.url.path == "/api/v1/auth/login" and request.method == "POST":
            # This is checked after the response
            pass
        
        response = await call_next(request)
        
        # Track failed login attempts
        if request.url.path == "/api/v1/auth/login" and request.method == "POST":
            if response.status_code == 401:
                self._record_failed_login(client_ip)
                if self._is_blocked(client_ip):
                    logger.warning("IP blocked for failed logins", ip=client_ip)
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "Too many failed login attempts. Try again later."},
                        headers={"Retry-After": str(self.config.failed_login_window_minutes * 60)},
                    )
            elif response.status_code == 200:
                self._clear_failed_logins(client_ip)
        
        return response
    
    def _record_failed_login(self, ip: str):
        """Record a failed login attempt."""
        now = time.time()
        window_start = now - (self.config.failed_login_window_minutes * 60)
        
        if ip not in self._failed_logins:
            self._failed_logins[ip] = []
        
        # Clean old entries
        self._failed_logins[ip] = [t for t in self._failed_logins[ip] if t > window_start]
        self._failed_logins[ip].append(now)
    
    def _clear_failed_logins(self, ip: str):
        """Clear failed login attempts for an IP."""
        if ip in self._failed_logins:
            del self._failed_logins[ip]
    
    def _is_blocked(self, ip: str) -> bool:
        """Check if IP is blocked for failed logins."""
        return len(self._failed_logins.get(ip, [])) >= self.config.failed_login_threshold


class SecurityMiddleware(BaseHTTPMiddleware):
    """Main security middleware combining all protections."""
    
    def __init__(
        self,
        app: ASGIApp,
        config: Optional[SecurityMiddlewareConfig] = None,
        rate_limiter=None,
        audit_logger=None,
        input_validator=None,
    ):
        super().__init__(app)
        self.config = config or get_security_middleware_config()
        self.rate_limiter = rate_limiter
        self.audit_logger = audit_logger
        self.input_validator = input_validator or get_input_validator()
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check if path is exempt
        if request.url.path in self.config.exempt_paths:
            return await call_next(request)
        
        # Set up audit context
        audit_context = {
            "request_id": str(uuid.uuid4()),
            "ip_address": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", ""),
            "method": request.method,
            "path": request.url.path,
        }
        set_audit_context(audit_context)
        
        try:
            # Rate limiting
            if self.config.enable_rate_limiting:
                await self._check_rate_limit(request)
            
            # Input validation
            if self.config.enable_input_validation:
                await self._validate_input(request)
            
            # Process request
            response = await call_next(request)
            
            # Add rate limit headers if available
            if hasattr(request.state, "rate_limit_headers"):
                for key, value in request.state.rate_limit_headers.items():
                    response.headers[key] = value
            
            # Audit log successful request
            if self.config.enable_audit_logging:
                self._audit_request(request, response, success=True)
            
            return response
            
        except ValueError as e:
            # Input validation errors - return 400
            if self.config.enable_audit_logging and self.audit_logger:
                self.audit_logger.log_invalid_input(
                    ip_address=audit_context["ip_address"],
                    endpoint=request.url.path,
                    input_type="validation",
                    error_details=str(e),
                    user_id=getattr(request.state, "user_id", None),
                )
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail={"error": str(e), "code": "VALIDATION_ERROR"})
        except Exception as e:
            # Audit log failed request
            if self.config.enable_audit_logging:
                self._audit_request(request, None, success=False, error=str(e))
            raise
        finally:
            clear_audit_context()
    
    async def _check_rate_limit(self, request: Request):
        """Check rate limit for request."""
        if self.rate_limiter is None:
            self.rate_limiter = await get_rate_limiter()
        
        # Determine identifier
        user_id = getattr(request.state, "user_id", None)
        identifier = f"user:{user_id}" if user_id else request.client.host if request.client else "unknown"
        
        # Check if admin
        is_admin = getattr(request.state, "is_admin", False)
        
        allowed, headers = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            endpoint=request.url.path,
            user_id=user_id,
            is_admin=is_admin,
        )
        
        if not allowed:
            # Audit rate limit exceeded
            if self.audit_logger:
                self.audit_logger.log_rate_limit_exceeded(
                    ip_address=request.client.host if request.client else "unknown",
                    endpoint=request.url.path,
                    limit=60,  # Default
                    window="minute",
                    user_id=user_id,
                )
            
            from fastapi import HTTPException
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers=headers,
            )
        
        # Store headers for response
        request.state.rate_limit_headers = headers
    
    async def _validate_input(self, request: Request):
        """Validate request input."""
        await self.input_validator.validate_request(
            request,
            validate_headers=self.config.validate_headers,
            validate_query=self.config.validate_query,
            validate_body=self.config.validate_body,
        )
    
    def _audit_request(self, request: Request, response: Optional[Response], success: bool, error: str = ""):
        """Audit log the request."""
        # This is a basic audit - specific events should use audit logger methods
        pass


class StreamingAbuseProtectionMiddleware(BaseHTTPMiddleware):
    """Specific abuse protection for streaming endpoints."""
    
    def __init__(self, app: ASGIApp, config: Optional[SecurityMiddlewareConfig] = None):
        super().__init__(app)
        self.config = config or get_security_middleware_config()
        self._streaming_sessions: Dict[str, Dict] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.config.enable_abuse_protection:
            return await call_next(request)
        
        # Only protect streaming endpoints
        if not request.url.path.startswith("/api/v1/chat/stream"):
            return await call_next(request)
        
        client_ip = request.client.host if request.client else "unknown"
        user_id = getattr(request.state, "user_id", None)
        session_key = f"{user_id or client_ip}"
        
        # Check concurrent streaming sessions
        now = time.time()
        if session_key in self._streaming_sessions:
            session = self._streaming_sessions[session_key]
            # Clean old sessions
            if now - session.get("start_time", 0) > 3600:  # 1 hour
                del self._streaming_sessions[session_key]
            elif session.get("active", False):
                logger.warning("Concurrent streaming session detected", session_key=session_key)
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Streaming session already active"},
                )
        
        # Mark session as active
        self._streaming_sessions[session_key] = {
            "start_time": now,
            "active": True,
            "token_count": 0,
        }
        
        try:
            response = await call_next(request)
            return response
        finally:
            # Mark session as inactive
            if session_key in self._streaming_sessions:
                self._streaming_sessions[session_key]["active"] = False


def create_security_middleware_stack(app: ASGIApp) -> ASGIApp:
    """Create the complete security middleware stack."""
    config = get_security_middleware_config()
    
    # Get shared instances (audit logger is sync, rate limiter is lazy)
    from app.security.audit import get_audit_logger
    from app.security.validation import get_input_validator
    
    audit_logger = get_audit_logger()
    input_validator = get_input_validator()
    
    # Order matters - outermost first
    # 1. Security headers (outermost - adds headers to all responses)
    if config.enable_security_headers:
        from app.security.headers import SecurityHeadersMiddleware, get_security_headers_config
        app = SecurityHeadersMiddleware(app, get_security_headers_config())
    
    # 2. Abuse protection
    if config.enable_abuse_protection:
        app = AbuseProtectionMiddleware(app, config)
    
    # 3. Streaming abuse protection
    if config.enable_abuse_protection:
        app = StreamingAbuseProtectionMiddleware(app, config)
    
    # 4. Main security middleware (rate limiting, input validation, audit)
    app = SecurityMiddleware(app, config, audit_logger=audit_logger, input_validator=input_validator)
    
    return app