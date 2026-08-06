"""Security package for KifPilot."""

from app.security.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    get_rate_limiter,
    rate_limit_dependency,
)
from app.security.audit import (
    AuditLogger,
    AuditEvent,
    AuditEventType,
    get_audit_logger,
)
from app.security.headers import (
    SecurityHeadersMiddleware,
    get_security_headers_config,
)
from app.security.validation import (
    InputValidator,
    ValidationConfig,
    get_input_validator,
    sanitize_string,
    sanitize_dict,
)
from app.security.upload_security import (
    UploadSecurityValidator,
    UploadSecurityConfig,
    get_upload_validator,
    validate_file_upload,
    SecureFilenameGenerator,
)
from app.security.secrets import (
    SecretsManager,
    get_secrets_manager,
    load_secret,
    rotate_secret,
)
from app.security.middleware import (
    SecurityMiddleware,
    AbuseProtectionMiddleware,
    create_security_middleware_stack,
)

__all__ = [
    # Rate Limiting
    "RateLimiter",
    "RateLimitConfig",
    "get_rate_limiter",
    "rate_limit_dependency",
    # Audit Logging
    "AuditLogger",
    "AuditEvent",
    "AuditEventType",
    "get_audit_logger",
    # Security Headers
    "SecurityHeadersMiddleware",
    "get_security_headers_config",
    # Input Validation
    "InputValidator",
    "ValidationConfig",
    "get_input_validator",
    "sanitize_string",
    "sanitize_dict",
    # Upload Security
    "UploadSecurityValidator",
    "UploadSecurityConfig",
    "get_upload_validator",
    "validate_file_upload",
    "SecureFilenameGenerator",
    # Secrets Management
    "SecretsManager",
    "get_secrets_manager",
    "load_secret",
    "rotate_secret",
    # Middleware
    "SecurityMiddleware",
    "AbuseProtectionMiddleware",
    "create_security_middleware_stack",
]