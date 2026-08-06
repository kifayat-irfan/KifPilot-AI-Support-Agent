from typing import Optional, Callable
from functools import wraps
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.core.config import get_settings
from app.core.database import get_db_session
from app.services.auth.jwt import verify_token, get_token_type
from app.services.auth.service import AuthService
from app.services.auth.repository import AuthRepository
from app.services.auth.exceptions import (
    InvalidTokenError,
    TokenExpiredError,
    PermissionDeniedError,
    InactiveUserError,
)
from app.database.models import User, Permission, UserRole

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_auth_service(db: AsyncSession = Depends(get_db_session)) -> AuthService:
    """Get auth service instance."""
    return AuthService(db)


async def get_current_user_id(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> str:
    """Get current user ID from token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = verify_token(token)
    if payload is None:
        raise credentials_exception

    if get_token_type(token) != "access":
        raise credentials_exception

    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Verify user exists and is active
    user = await auth_service._repo.get_user_by_id(user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user_id


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Get current user object."""
    user = await auth_service._repo.get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user


def require_permission(permission: Permission) -> Callable:
    """Dependency to require a specific permission."""
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> User:
        has_perm = await auth_service._repo.user_has_permission(current_user.id, permission)
        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value}",
            )
        return current_user
    return permission_checker


def require_role(role: UserRole) -> Callable:
    """Dependency to require a specific role."""
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> User:
        has_role = await auth_service._repo.user_has_role(current_user.id, role)
        if not has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role required: {role.value}",
            )
        return current_user
    return role_checker


def require_any_permission(*permissions: Permission) -> Callable:
    """Dependency to require at least one of the specified permissions."""
    async def permission_checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> User:
        for perm in permissions:
            has_perm = await auth_service._repo.user_has_permission(current_user.id, perm)
            if has_perm:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: requires one of {[p.value for p in permissions]}",
        )
    return permission_checker


def require_any_role(*roles: UserRole) -> Callable:
    """Dependency to require at least one of the specified roles."""
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service),
    ) -> User:
        for role in roles:
            has_role = await auth_service._repo.user_has_role(current_user.id, role)
            if has_role:
                return current_user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role required: requires one of {[r.value for r in roles]}",
        )
    return role_checker


# Convenience dependencies for common permissions
require_upload_documents = require_permission(Permission.UPLOAD_DOCUMENTS)
require_delete_documents = require_permission(Permission.DELETE_DOCUMENTS)
require_chat = require_permission(Permission.CHAT)
require_view_sessions = require_permission(Permission.VIEW_SESSIONS)
require_manage_users = require_permission(Permission.MANAGE_USERS)
require_manage_settings = require_permission(Permission.MANAGE_SETTINGS)

# Convenience dependencies for common roles
require_admin = require_role(UserRole.ADMIN)
require_manager = require_any_role(UserRole.ADMIN, UserRole.MANAGER)
require_editor = require_any_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR)
require_viewer = require_any_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR, UserRole.VIEWER)