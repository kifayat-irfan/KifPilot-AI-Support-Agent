from typing import Optional, List, Set
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import timedelta

from app.services.auth.repository import AuthRepository
from app.services.auth.password import hash_password, verify_password
from app.services.auth.jwt import (
    create_access_token,
    create_refresh_token,
    verify_token,
    get_token_type,
)
from app.services.auth.schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    LoginRequest,
    Token,
    RoleResponse,
    PermissionResponse,
    RegisterRequest,
)
from app.services.auth.exceptions import (
    UserNotFoundError,
    InvalidCredentialsError,
    InactiveUserError,
    InvalidTokenError,
    TokenExpiredError,
    PermissionDeniedError,
    RoleNotFoundError,
)
from app.database.models import User, Role, PermissionModel, UserRole, Permission
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthService:
    """Main authentication service."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = AuthRepository(session)

    # User registration and authentication
    async def register(self, request: RegisterRequest) -> UserResponse:
        """Register a new user."""
        hashed_password = hash_password(request.password)
        user = await self._repo.create_user(
            email=request.email,
            username=request.username,
            hashed_password=hashed_password,
        )

        # Assign default role (viewer)
        await self._repo.assign_role_to_user(user.id, UserRole.VIEWER)

        # Reload user with roles
        user = await self._repo.get_user_by_id(user.id)
        return UserResponse.model_validate(user)

    async def login(self, request: LoginRequest) -> Token:
        """Authenticate a user and return tokens."""
        user = await self._repo.get_user_by_username_or_email(request.username)
        if not user:
            logger.warning("Login failed: user not found", username=request.username)
            raise InvalidCredentialsError()

        if not verify_password(request.password, user.hashed_password):
            logger.warning("Login failed: invalid password", username=request.username)
            raise InvalidCredentialsError()

        if not user.is_active:
            logger.warning("Login failed: user inactive", username=request.username)
            raise InactiveUserError()

        # Create tokens
        access_token = create_access_token({"sub": user.id})
        refresh_token = create_refresh_token({"sub": user.id})

        logger.info("User logged in", user_id=user.id, username=user.username)
        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def refresh_token(self, refresh_token: str) -> Token:
        """Refresh access token using refresh token."""
        payload = verify_token(refresh_token)
        if not payload:
            raise InvalidTokenError("Invalid refresh token")

        if get_token_type(refresh_token) != "refresh":
            raise InvalidTokenError("Token is not a refresh token")

        user_id = payload.get("sub")
        if not user_id:
            raise InvalidTokenError("Invalid token payload")

        user = await self._repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        if not user.is_active:
            raise InactiveUserError()

        # Create new tokens
        new_access_token = create_access_token({"sub": user.id})
        new_refresh_token = create_refresh_token({"sub": user.id})

        logger.info("Token refreshed", user_id=user.id)
        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
        )

    async def logout(self, user_id: str) -> None:
        """Logout a user (in a real app, you might blacklist the token)."""
        logger.info("User logged out", user_id=user_id)

    # User management
    async def get_current_user(self, user_id: str) -> UserResponse:
        """Get current user by ID."""
        user = await self._repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)
        return UserResponse.model_validate(user)

    async def update_user(self, user_id: str, request: UserUpdate) -> UserResponse:
        """Update a user."""
        user = await self._repo.update_user(
            user_id=user_id,
            email=request.email,
            username=request.username,
            is_active=request.is_active,
        )
        return UserResponse.model_validate(user)

    async def change_password(self, user_id: str, current_password: str, new_password: str) -> None:
        """Change a user's password."""
        user = await self._repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        if not verify_password(current_password, user.hashed_password):
            raise InvalidCredentialsError()

        hashed_password = hash_password(new_password)
        await self._repo.update_user_password(user_id, hashed_password)
        logger.info("Password changed", user_id=user_id)

    async def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        await self._repo.delete_user(user_id)

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[UserResponse]:
        """List users with pagination."""
        users = await self._repo.list_users(skip=skip, limit=limit)
        return [UserResponse.model_validate(u) for u in users]

    # Role management
    async def assign_role(self, user_id: str, role_name: UserRole) -> UserResponse:
        """Assign a role to a user."""
        user = await self._repo.assign_role_to_user(user_id, role_name)
        return UserResponse.model_validate(user)

    async def remove_role(self, user_id: str, role_name: UserRole) -> UserResponse:
        """Remove a role from a user."""
        user = await self._repo.remove_role_from_user(user_id, role_name)
        return UserResponse.model_validate(user)

    async def get_user_roles(self, user_id: str) -> List[RoleResponse]:
        """Get all roles for a user."""
        user = await self._repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        return [RoleResponse.model_validate(role) for role in user.roles]

    async def list_roles(self) -> List[RoleResponse]:
        """List all roles."""
        roles = await self._repo.list_roles()
        return [RoleResponse.model_validate(r) for r in roles]

    # Permission management
    async def assign_permission_to_role(self, role_name: UserRole, permission_name: Permission) -> RoleResponse:
        """Assign a permission to a role."""
        role = await self._repo.assign_permission_to_role(role_name, permission_name)
        return RoleResponse.model_validate(role)

    async def list_permissions(self) -> List[PermissionResponse]:
        """List all permissions."""
        permissions = await self._repo.list_permissions()
        return [PermissionResponse.model_validate(p) for p in permissions]

    # Permission checking
    async def check_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        has_perm = await self._repo.user_has_permission(user_id, permission)
        if not has_perm:
            logger.warning("Permission denied", user_id=user_id, permission=permission.value)
        return has_perm

    async def require_permission(self, user_id: str, permission: Permission) -> None:
        """Require a specific permission, raise if not granted."""
        has_perm = await self.check_permission(user_id, permission)
        if not has_perm:
            raise PermissionDeniedError(permission.value)

    async def check_role(self, user_id: str, role_name: UserRole) -> bool:
        """Check if a user has a specific role."""
        return await self._repo.user_has_role(user_id, role_name)

    async def require_role(self, user_id: str, role_name: UserRole) -> None:
        """Require a specific role, raise if not granted."""
        has_role = await self.check_role(user_id, role_name)
        if not has_role:
            raise PermissionDeniedError(f"role:{role_name.value}")

    async def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        return await self._repo.get_user_permissions(user_id)

    # Token validation
    async def validate_token(self, token: str) -> Optional[str]:
        """Validate an access token and return user ID."""
        payload = verify_token(token)
        if not payload:
            return None

        if get_token_type(token) != "access":
            return None

        user_id = payload.get("sub")
        if not user_id:
            return None

        user = await self._repo.get_user_by_id(user_id)
        if not user or not user.is_active:
            return None

        return user_id