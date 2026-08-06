"""Audit logging for KifPilot."""

import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field, asdict
from contextvars import ContextVar

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class AuditEventType(str, Enum):
    """Types of audit events."""
    # Authentication
    LOGIN = "login"
    LOGOUT = "logout"
    LOGIN_FAILED = "login_failed"
    TOKEN_REFRESH = "token_refresh"
    PASSWORD_CHANGE = "password_change"
    PASSWORD_RESET = "password_reset"
    
    # Authorization
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REVOKED = "role_revoked"
    
    # Documents
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_DOWNLOAD = "document_download"
    DOCUMENT_VIEW = "document_view"
    DOCUMENT_UPDATE = "document_update"
    
    # Knowledge Base
    KB_CREATE = "kb_create"
    KB_UPDATE = "kb_update"
    KB_DELETE = "kb_delete"
    KB_VIEW = "kb_view"
    
    # Organization
    ORG_CREATE = "org_create"
    ORG_UPDATE = "org_update"
    ORG_DELETE = "org_delete"
    ORG_MEMBER_ADD = "org_member_add"
    ORG_MEMBER_REMOVE = "org_member_remove"
    ORG_MEMBER_ROLE_CHANGE = "org_member_role_change"
    
    # Admin
    ADMIN_USER_CREATE = "admin_user_create"
    ADMIN_USER_UPDATE = "admin_user_update"
    ADMIN_USER_DELETE = "admin_user_delete"
    ADMIN_USER_SUSPEND = "admin_user_suspend"
    ADMIN_SETTINGS_CHANGE = "admin_settings_change"
    
    # Chat
    CHAT_SESSION_CREATE = "chat_session_create"
    CHAT_SESSION_DELETE = "chat_session_delete"
    CHAT_MESSAGE_SEND = "chat_message_send"
    
    # Security
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"
    INVALID_INPUT = "invalid_input"
    MALFORMED_REQUEST = "malformed_request"


@dataclass
class AuditEvent:
    """Audit event record."""
    event_type: AuditEventType
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    # Actor
    user_id: Optional[str] = None
    username: Optional[str] = None
    organization_id: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Target
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None
    
    # Details
    action: Optional[str] = None
    status: str = "success"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Request context
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)


# Context variables for request context
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_context', default=None)


def set_audit_context(context: Dict[str, Any]):
    """Set audit context for current request."""
    _request_context.set(context)


def clear_audit_context():
    """Clear audit context."""
    _request_context.set(None)


def get_audit_context() -> Optional[Dict[str, Any]]:
    """Get current audit context."""
    return _request_context.get()


class AuditLogger:
    """Audit logger for security events."""
    
    def __init__(self):
        self._enabled = True
        self._log_to_file = settings.APP_ENV == "production"
        self._file_path = "./logs/audit.log"
    
    def log(self, event: AuditEvent):
        """Log an audit event."""
        if not self._enabled:
            return
        
        # Add context from request if available
        context = get_audit_context()
        if context:
            if not event.request_id:
                event.request_id = context.get("request_id")
            if not event.trace_id:
                event.trace_id = context.get("trace_id")
            if not event.span_id:
                event.span_id = context.get("span_id")
            if not event.ip_address:
                event.ip_address = context.get("ip_address")
            if not event.user_agent:
                event.user_agent = context.get("user_agent")
            if not event.user_id:
                event.user_id = context.get("user_id")
            if not event.username:
                event.username = context.get("username")
            if not event.organization_id:
                event.organization_id = context.get("organization_id")
        
        # Log to structured logger
        logger.info(
            f"Audit: {event.event_type.value}",
            audit_event=event.to_dict(),
        )
        
        # Write to file in production
        if self._log_to_file:
            self._write_to_file(event)
    
    def _write_to_file(self, event: AuditEvent):
        """Write audit event to file."""
        try:
            import os
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            with open(self._file_path, "a", encoding="utf-8") as f:
                f.write(event.to_json() + "\n")
        except Exception as e:
            logger.error("Failed to write audit log to file", error=str(e))
    
    # Convenience methods for common events
    def log_login(
        self,
        user_id: str,
        username: str,
        organization_id: str,
        ip_address: str,
        user_agent: str,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """Log login attempt."""
        self.log(AuditEvent(
            event_type=AuditEventType.LOGIN if success else AuditEventType.LOGIN_FAILED,
            user_id=user_id,
            username=username,
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status="success" if success else "failure",
            error_message=error_message,
            action="login",
        ))
    
    def log_logout(
        self,
        user_id: str,
        username: str,
        organization_id: str,
        ip_address: str,
    ):
        """Log logout."""
        self.log(AuditEvent(
            event_type=AuditEventType.LOGOUT,
            user_id=user_id,
            username=username,
            organization_id=organization_id,
            ip_address=ip_address,
            action="logout",
        ))
    
    def log_permission_denied(
        self,
        user_id: str,
        username: str,
        organization_id: str,
        resource_type: str,
        resource_id: str,
        required_permission: str,
        ip_address: str,
    ):
        """Log permission denied."""
        self.log(AuditEvent(
            event_type=AuditEventType.PERMISSION_DENIED,
            user_id=user_id,
            username=username,
            organization_id=organization_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            status="failure",
            action="access_denied",
            metadata={"required_permission": required_permission},
        ))
    
    def log_document_upload(
        self,
        user_id: str,
        username: str,
        organization_id: str,
        document_id: str,
        document_name: str,
        file_size: int,
        mime_type: str,
        ip_address: str,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """Log document upload."""
        self.log(AuditEvent(
            event_type=AuditEventType.DOCUMENT_UPLOAD,
            user_id=user_id,
            username=username,
            organization_id=organization_id,
            ip_address=ip_address,
            resource_type="document",
            resource_id=document_id,
            resource_name=document_name,
            status="success" if success else "failure",
            error_message=error_message,
            action="upload",
            metadata={"file_size": file_size, "mime_type": mime_type},
        ))
    
    def log_document_delete(
        self,
        user_id: str,
        username: str,
        organization_id: str,
        document_id: str,
        document_name: str,
        ip_address: str,
    ):
        """Log document deletion."""
        self.log(AuditEvent(
            event_type=AuditEventType.DOCUMENT_DELETE,
            user_id=user_id,
            username=username,
            organization_id=organization_id,
            ip_address=ip_address,
            resource_type="document",
            resource_id=document_id,
            resource_name=document_name,
            action="delete",
        ))
    
    def log_role_change(
        self,
        actor_user_id: str,
        actor_username: str,
        target_user_id: str,
        target_username: str,
        organization_id: str,
        old_role: str,
        new_role: str,
        ip_address: str,
    ):
        """Log role change."""
        self.log(AuditEvent(
            event_type=AuditEventType.ORG_MEMBER_ROLE_CHANGE,
            user_id=actor_user_id,
            username=actor_username,
            organization_id=organization_id,
            ip_address=ip_address,
            resource_type="user",
            resource_id=target_user_id,
            resource_name=target_username,
            action="role_change",
            metadata={"old_role": old_role, "new_role": new_role},
        ))
    
    def log_admin_action(
        self,
        admin_user_id: str,
        admin_username: str,
        action: str,
        target_type: str,
        target_id: str,
        target_name: str,
        organization_id: str,
        ip_address: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Log admin action."""
        event_type_map = {
            "create_user": AuditEventType.ADMIN_USER_CREATE,
            "update_user": AuditEventType.ADMIN_USER_UPDATE,
            "delete_user": AuditEventType.ADMIN_USER_DELETE,
            "suspend_user": AuditEventType.ADMIN_USER_SUSPEND,
            "change_settings": AuditEventType.ADMIN_SETTINGS_CHANGE,
        }
        self.log(AuditEvent(
            event_type=event_type_map.get(action, AuditEventType.ADMIN_SETTINGS_CHANGE),
            user_id=admin_user_id,
            username=admin_username,
            organization_id=organization_id,
            ip_address=ip_address,
            resource_type=target_type,
            resource_id=target_id,
            resource_name=target_name,
            action=action,
            metadata=metadata or {},
        ))
    
    def log_suspicious_activity(
        self,
        ip_address: str,
        user_agent: str,
        activity_type: str,
        details: Dict[str, Any],
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None,
    ):
        """Log suspicious activity."""
        self.log(AuditEvent(
            event_type=AuditEventType.SUSPICIOUS_ACTIVITY,
            user_id=user_id,
            organization_id=organization_id,
            ip_address=ip_address,
            user_agent=user_agent,
            action=activity_type,
            status="warning",
            metadata=details,
        ))
    
    def log_rate_limit_exceeded(
        self,
        ip_address: str,
        endpoint: str,
        limit: int,
        window: str,
        user_id: Optional[str] = None,
    ):
        """Log rate limit exceeded."""
        self.log(AuditEvent(
            event_type=AuditEventType.RATE_LIMIT_EXCEEDED,
            user_id=user_id,
            ip_address=ip_address,
            resource_type="endpoint",
            resource_id=endpoint,
            action="rate_limit_exceeded",
            status="warning",
            metadata={"limit": limit, "window": window},
        ))
    
    def log_invalid_input(
        self,
        ip_address: str,
        endpoint: str,
        input_type: str,
        error_details: str,
        user_id: Optional[str] = None,
    ):
        """Log invalid input rejection."""
        self.log(AuditEvent(
            event_type=AuditEventType.INVALID_INPUT,
            user_id=user_id,
            ip_address=ip_address,
            resource_type="endpoint",
            resource_id=endpoint,
            action="invalid_input_rejected",
            status="warning",
            metadata={"input_type": input_type, "error": error_details},
        ))


_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger