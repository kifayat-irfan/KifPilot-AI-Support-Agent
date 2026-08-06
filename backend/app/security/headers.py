"""Security headers for KifPilot."""

from typing import Optional, Dict, List
from dataclasses import dataclass, field
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class SecurityHeadersConfig:
    """Configuration for security headers."""
    # Content Security Policy
    csp_enabled: bool = True
    csp_policy: str = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' wss: https:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    csp_report_only: bool = False
    
    # Strict Transport Security
    hsts_enabled: bool = True
    hsts_max_age: int = 31536000  # 1 year
    hsts_include_subdomains: bool = True
    hsts_preload: bool = True
    
    # Frame Options
    frame_options: str = "DENY"
    
    # Content Type Options
    content_type_options: str = "nosniff"
    
    # Referrer Policy
    referrer_policy: str = "strict-origin-when-cross-origin"
    
    # Permissions Policy
    permissions_policy: str = (
        "accelerometer=(), "
        "camera=(), "
        "geolocation=(), "
        "gyroscope=(), "
        "magnetometer=(), "
        "microphone=(), "
        "payment=(), "
        "usb=()"
    )
    
    # Cross-Origin policies
    cross_origin_embedder_policy: str = "require-corp"
    cross_origin_opener_policy: str = "same-origin"
    cross_origin_resource_policy: str = "same-origin"
    
    # XSS Protection (legacy but still useful)
    xss_protection: str = "1; mode=block"
    
    # Expect-CT
    expect_ct: str = "max-age=86400, enforce"
    
    # Custom headers
    custom_headers: Dict[str, str] = field(default_factory=dict)


def get_security_headers_config() -> SecurityHeadersConfig:
    """Get security headers configuration."""
    config = SecurityHeadersConfig()
    
    # Adjust for development
    if settings.DEBUG:
        config.csp_policy = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:* ws://localhost:*; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' http://localhost:*; "
            "style-src 'self' 'unsafe-inline' http://localhost:*; "
            "img-src 'self' data: https: http://localhost:*; "
            "font-src 'self' data: http://localhost:*; "
            "connect-src 'self' wss: https: http://localhost:* ws://localhost:*; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        )
        config.hsts_enabled = False
        config.cross_origin_embedder_policy = "unsafe-none"
    
    # Allow CSP override from environment
    import os
    if csp_env := os.getenv("CSP_POLICY"):
        config.csp_policy = csp_env
    
    return config


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""
    
    def __init__(self, app, config: Optional[SecurityHeadersConfig] = None):
        super().__init__(app)
        self.config = config or get_security_headers_config()
    
    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        
        # Add security headers
        self._add_security_headers(response, request)
        
        return response
    
    def _add_security_headers(self, response: Response, request: Request):
        """Add security headers to response."""
        config = self.config
        
        # Content Security Policy
        if config.csp_enabled:
            header_name = "Content-Security-Policy-Report-Only" if config.csp_report_only else "Content-Security-Policy"
            response.headers[header_name] = config.csp_policy
        
        # Strict Transport Security
        if config.hsts_enabled and request.url.scheme == "https":
            hsts_value = f"max-age={config.hsts_max_age}"
            if config.hsts_include_subdomains:
                hsts_value += "; includeSubDomains"
            if config.hsts_preload:
                hsts_value += "; preload"
            response.headers["Strict-Transport-Security"] = hsts_value
        
        # X-Frame-Options
        response.headers["X-Frame-Options"] = config.frame_options
        
        # X-Content-Type-Options
        response.headers["X-Content-Type-Options"] = config.content_type_options
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = config.referrer_policy
        
        # Permissions Policy
        response.headers["Permissions-Policy"] = config.permissions_policy
        
        # Cross-Origin policies
        response.headers["Cross-Origin-Embedder-Policy"] = config.cross_origin_embedder_policy
        response.headers["Cross-Origin-Opener-Policy"] = config.cross_origin_opener_policy
        response.headers["Cross-Origin-Resource-Policy"] = config.cross_origin_resource_policy
        
        # XSS Protection
        response.headers["X-XSS-Protection"] = config.xss_protection
        
        # Expect-CT
        response.headers["Expect-CT"] = config.expect_ct
        
        # Custom headers
        for key, value in config.custom_headers.items():
            response.headers[key] = value
        
        # Remove server header
        if "server" in response.headers:
            del response.headers["server"]
        
        # Remove X-Powered-By if present
        if "x-powered-by" in response.headers:
            del response.headers["x-powered-by"]