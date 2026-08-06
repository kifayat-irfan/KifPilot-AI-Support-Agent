"""Input validation and sanitization for KifPilot."""

import re
import html
import json
from typing import Any, Dict, List, Optional, Union, Set
from dataclasses import dataclass, field
from urllib.parse import unquote
from starlette.requests import Request
from starlette.datastructures import Headers, FormData, UploadFile

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class ValidationConfig:
    """Configuration for input validation."""
    # String limits
    max_string_length: int = 10000
    max_header_length: int = 8192
    max_query_param_length: int = 2048
    max_json_depth: int = 10
    max_json_keys: int = 1000
    max_array_length: int = 10000
    
    # Allowed characters
    allow_unicode: bool = True
    allow_newlines_in_strings: bool = False
    
    # HTML/Script protection
    strip_html: bool = True
    strip_scripts: bool = True
    strip_sql: bool = True
    
    # Path traversal
    block_path_traversal: bool = True
    
    # Command injection
    block_command_injection: bool = True
    
    # Custom patterns to block
    custom_block_patterns: List[str] = field(default_factory=list)


def get_validation_config() -> ValidationConfig:
    """Get validation configuration."""
    config = ValidationConfig()
    
    # Adjust for production
    if settings.APP_ENV == "production":
        config.max_string_length = 5000
        config.max_query_param_length = 1024
    
    return config


class InputValidator:
    """Validates and sanitizes input data."""
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC|EXECUTE)\b)",
        r"(--|;|\bOR\b|\bAND\b)\s*\d+\s*=\s*\d+",
        r"'\s*(OR|AND)\s*'",
        r"(EXEC|EXECUTE)\s*\(",
        r"xp_cmdshell",
        r"sp_executesql",
    ]
    
    # Command injection patterns
    CMD_PATTERNS = [
        r"[;&|`$()]",
        r"\b(cat|ls|pwd|whoami|id|uname|ps|netstat|ifconfig|ipconfig)\b",
        r"\b(wget|curl|nc|telnet|ssh|ftp|tftp)\b",
        r"\b(rm|mv|cp|chmod|chown|kill|killall)\b",
        r"\b(python|perl|ruby|php|node|java|go|rust)\b.*-e",
        r"/bin/(bash|sh|zsh|fish)",
        r"/etc/passwd",
        r"/etc/shadow",
    ]
    
    # Path traversal patterns
    PATH_TRAVERSAL_PATTERNS = [
        r"\.\./",
        r"\.\.\\",
        r"%2e%2e%2f",
        r"%2e%2e%5c",
        r"\.\.%2f",
        r"\.\.%5c",
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"onload\s*=",
        r"onerror\s*=",
        r"onclick\s*=",
        r"onmouseover\s*=",
        r"onfocus\s*=",
        r"onblur\s*=",
        r"onchange\s*=",
        r"onsubmit\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
        r"<applet",
        r"<meta",
        r"<link",
        r"expression\s*\(",
        r"url\s*\(",
        r"@import",
        r"behaviour\s*:",
        r"binding\s*:",
    ]
    
    def __init__(self, config: Optional[ValidationConfig] = None):
        self.config = config or get_validation_config()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for performance."""
        self._sql_regex = [re.compile(p, re.IGNORECASE) for p in self.SQL_PATTERNS]
        self._cmd_regex = [re.compile(p, re.IGNORECASE) for p in self.CMD_PATTERNS]
        self._path_regex = [re.compile(p, re.IGNORECASE) for p in self.PATH_TRAVERSAL_PATTERNS]
        self._xss_regex = [re.compile(p, re.IGNORECASE) for p in self.XSS_PATTERNS]
        self._custom_regex = [re.compile(p, re.IGNORECASE) for p in self.config.custom_block_patterns]
    
    def validate_string(self, value: str, field_name: str = "input") -> str:
        """Validate and sanitize a string value."""
        if not isinstance(value, str):
            raise ValueError(f"{field_name}: Expected string, got {type(value).__name__}")
        
        # Check length
        if len(value) > self.config.max_string_length:
            raise ValueError(f"{field_name}: String too long (max {self.config.max_string_length})")
        
        # Check for null bytes
        if "\x00" in value:
            raise ValueError(f"{field_name}: Null bytes not allowed")
        
        # URL decode to catch encoded attacks
        decoded = unquote(value)
        if decoded != value:
            # Recursively check decoded value
            self.validate_string(decoded, field_name)
        
        # Check for SQL injection
        if self.config.strip_sql:
            for pattern in self._sql_regex:
                if pattern.search(value):
                    raise ValueError(f"{field_name}: Potential SQL injection detected")
        
        # Check for command injection
        if self.config.block_command_injection:
            for pattern in self._cmd_regex:
                if pattern.search(value):
                    raise ValueError(f"{field_name}: Potential command injection detected")
        
        # Check for path traversal
        if self.config.block_path_traversal:
            for pattern in self._path_regex:
                if pattern.search(value):
                    raise ValueError(f"{field_name}: Path traversal attempt detected")
        
        # Check for XSS
        if self.config.strip_scripts:
            for pattern in self._xss_regex:
                if pattern.search(value):
                    raise ValueError(f"{field_name}: Potential XSS detected")
        
        # Check custom patterns
        for pattern in self._custom_regex:
            if pattern.search(value):
                raise ValueError(f"{field_name}: Blocked pattern detected")
        
        # Sanitize
        sanitized = self.sanitize_string(value)
        
        return sanitized
    
    def sanitize_string(self, value: str) -> str:
        """Sanitize a string value."""
        # HTML escape
        if self.config.strip_html:
            value = html.escape(value, quote=True)
        
        # Remove control characters except newlines/tabs if allowed
        if not self.config.allow_newlines_in_strings:
            value = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", value)
        else:
            value = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", value)
        
        # Normalize whitespace
        value = re.sub(r"\s+", " ", value).strip()
        
        return value
    
    def validate_dict(self, data: Dict[str, Any], prefix: str = "", depth: int = 0) -> Dict[str, Any]:
        """Validate and sanitize a dictionary."""
        if depth > self.config.max_json_depth:
            raise ValueError(f"JSON depth exceeds maximum ({self.config.max_json_depth})")
        
        if len(data) > self.config.max_json_keys:
            raise ValueError(f"Too many keys in object (max {self.config.max_json_keys})")
        
        result = {}
        for key, value in data.items():
            # Validate key
            if not isinstance(key, str):
                raise ValueError(f"Object keys must be strings, got {type(key).__name__}")
            sanitized_key = self.sanitize_string(key)
            
            full_key = f"{prefix}.{sanitized_key}" if prefix else sanitized_key
            
            # Validate value
            if isinstance(value, str):
                result[sanitized_key] = self.validate_string(value, full_key)
            elif isinstance(value, dict):
                result[sanitized_key] = self.validate_dict(value, full_key, depth + 1)
            elif isinstance(value, list):
                result[sanitized_key] = self.validate_list(value, full_key, depth + 1)
            elif isinstance(value, (int, float, bool)) or value is None:
                result[sanitized_key] = value
            else:
                raise ValueError(f"{full_key}: Unsupported value type {type(value).__name__}")
        
        return result
    
    def validate_list(self, data: List[Any], prefix: str = "", depth: int = 0) -> List[Any]:
        """Validate and sanitize a list."""
        if depth > self.config.max_json_depth:
            raise ValueError(f"JSON depth exceeds maximum ({self.config.max_json_depth})")
        
        if len(data) > self.config.max_array_length:
            raise ValueError(f"Array too long (max {self.config.max_array_length})")
        
        result = []
        for i, value in enumerate(data):
            full_key = f"{prefix}[{i}]"
            
            if isinstance(value, str):
                result.append(self.validate_string(value, full_key))
            elif isinstance(value, dict):
                result.append(self.validate_dict(value, full_key, depth + 1))
            elif isinstance(value, list):
                result.append(self.validate_list(value, full_key, depth + 1))
            elif isinstance(value, (int, float, bool)) or value is None:
                result.append(value)
            else:
                raise ValueError(f"{full_key}: Unsupported value type {type(value).__name__}")
        
        return result
    
    async def validate_request(
        self,
        request: Request,
        validate_headers: bool = True,
        validate_query: bool = True,
        validate_body: bool = True,
    ) -> Request:
        """Validate entire request."""
        # Validate headers
        if validate_headers:
            await self._validate_headers(request.headers)
        
        # Validate query parameters
        if validate_query:
            self._validate_query_params(request.query_params)
        
        # Validate body
        if validate_body and request.method in ("POST", "PUT", "PATCH"):
            await self._validate_body(request)
        
        return request
    
    async def _validate_headers(self, headers: Headers):
        """Validate request headers."""
        # Headers that commonly contain special characters and should be skipped for injection validation
        skip_injection_validation = {
            "content-type",
            "content-length",
            "content-disposition",
            "cookie",
            "set-cookie",
            "authorization",
            "referer",
            "origin",
            "user-agent",
        }
        
        for key, value in headers.items():
            # Skip internal headers
            if key.lower().startswith("x-") and key.lower() not in ("x-forwarded-for", "x-real-ip"):
                continue
            
            if len(key) > self.config.max_header_length:
                raise ValueError(f"Header name too long: {key}")
            if len(value) > self.config.max_header_length:
                raise ValueError(f"Header value too long: {key}")
            
            # Validate header values - skip injection validation for known safe headers
            if key.lower() in skip_injection_validation:
                # Still check length and null bytes
                if "\x00" in value:
                    raise ValueError(f"header:{key}: Null bytes not allowed")
                # URL decode to catch encoded attacks
                from urllib.parse import unquote
                decoded = unquote(value)
                if decoded != value:
                    self.validate_string(decoded, f"header:{key}")
            else:
                self.validate_string(value, f"header:{key}")
    
    def _validate_query_params(self, query_params):
        """Validate query parameters."""
        for key, value in query_params.multi_items():
            if len(key) > self.config.max_query_param_length:
                raise ValueError(f"Query parameter name too long: {key}")
            if len(value) > self.config.max_query_param_length:
                raise ValueError(f"Query parameter value too long: {key}")
            
            self.validate_string(value, f"query:{key}")
    
    async def _validate_body(self, request: Request):
        """Validate request body."""
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            body = await request.json()
            if isinstance(body, dict):
                self.validate_dict(body)
            elif isinstance(body, list):
                self.validate_list(body)
            else:
                raise ValueError("JSON body must be object or array")
        
        elif "application/x-www-form-urlencoded" in content_type:
            form = await request.form()
            for key, value in form.multi_items():
                if isinstance(value, str):
                    self.validate_string(value, f"form:{key}")
        
        elif "multipart/form-data" in content_type:
            form = await request.form()
            for key, value in form.multi_items():
                if isinstance(value, str):
                    self.validate_string(value, f"form:{key}")
                # Files are validated separately by upload_security


def sanitize_string(value: str, config: Optional[ValidationConfig] = None) -> str:
    """Quick sanitize function for simple cases."""
    validator = InputValidator(config)
    return validator.sanitize_string(value)


def sanitize_dict(data: Dict[str, Any], config: Optional[ValidationConfig] = None) -> Dict[str, Any]:
    """Quick sanitize function for dictionaries."""
    validator = InputValidator(config)
    return validator.validate_dict(data)


_input_validator: Optional[InputValidator] = None


def get_input_validator() -> InputValidator:
    """Get or create the global input validator."""
    global _input_validator
    if _input_validator is None:
        _input_validator = InputValidator()
    return _input_validator