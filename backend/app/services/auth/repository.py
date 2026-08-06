from typing import List, Optional, Set
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload

from app.database.models import User, Role, PermissionModel, UserRole, Permission
from app.services.auth.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError,
    RoleNotFoundError,
    PermissionNotFoundError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class AuthRepository:
    """Repository for authentication database operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # User operations
    async def create_user(
        self,
        email: str,
        username: str,
        hashed_password: str,
        is_active: bool = True
    ) -> User:
        """Create a new user."""
        # Check if user already exists
        existing_email = await self.get_user_by_email(email)
        if existing_email:
            raise UserAlreadyExistsError("email", email)

        existing_username = await self.get_user_by_username(username)
        if existing_username:
            raise UserAlreadyExistsError("username", username)

        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            is_active=is_active
        )
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)

        logger.info("User created", user_id=user.id, email=email, username=username)
        return user

    async def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID with roles and permissions loaded."""
        result = await self._session.execute(
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email with roles and permissions loaded."""
        result = await self._session.execute(
            select(User)
            .where(User.email == email)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username with roles and permissions loaded."""
        result = await self._session.execute(
            select(User)
            .where(User.username == username)
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_user_by_username_or_email(self, identifier: str) -> Optional[User]:
        """Get a user by username or email."""
        result = await self._session.execute(
            select(User)
            .where((User.username == identifier) | (User.email == identifier))
            .options(selectinload(User.roles).selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def update_user(
        self,
        user_id: str,
        email: Optional[str] = None,
        username: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> User:
        """Update a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        if email is not None:
            existing = await self.get_user_by_email(email)
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError("email", email)
            user.email = email

        if username is not None:
            existing = await self.get_user_by_username(username)
            if existing and existing.id != user_id:
                raise UserAlreadyExistsError("username", username)
            user.username = username

        if is_active is not None:
            user.is_active = is_active

        await self._session.flush()
        await self._session.refresh(user)

        logger.info("User updated", user_id=user_id)
        return user

    async def update_user_password(self, user_id: str, hashed_password: str) -> User:
        """Update a user's password."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        user.hashed_password = hashed_password
        await self._session.flush()
        await self._session.refresh(user)

        logger.info("User password updated", user_id=user_id)
        return user

    async def delete_user(self, user_id: str) -> None:
        """Delete a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        await self._session.delete(user)
        await self._session.flush()

        logger.info("User deleted", user_id=user_id)

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        """List users with pagination."""
        result = await self._session.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    # Role operations
    async def get_role_by_name(self, name: UserRole) -> Optional[Role]:
        """Get a role by name with permissions loaded."""
        result = await self._session.execute(
            select(Role)
            .where(Role.name == name)
            .options(selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_role_by_id(self, role_id: str) -> Optional[Role]:
        """Get a role by ID with permissions loaded."""
        result = await self._session.execute(
            select(Role)
            .where(Role.id == role_id)
            .options(selectinload(Role.permissions))
        )
        return result.scalar_one_or_none()

    async def get_or_create_role(self, name: UserRole, description: Optional[str] = None) -> Role:
        """Get an existing role or create a new one."""
        role = await self.get_role_by_name(name)
        if not role:
            role = Role(name=name, description=description)
            self._session.add(role)
            await self._session.flush()
            await self._session.refresh(role)
            logger.info("Role created", role_id=role.id, name=name.value)
        return role

    async def list_roles(self) -> List[Role]:
        """List all roles with permissions loaded."""
        result = await self._session.execute(
            select(Role).options(selectinload(Role.permissions))
        )
        return list(result.scalars().all())

    async def assign_role_to_user(self, user_id: str, role_name: UserRole) -> User:
        """Assign a role to a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        role = await self.get_or_create_role(role_name)
        if role not in user.roles:
            user.roles.append(role)
            await self._session.flush()
            await self._session.refresh(user)
            logger.info("Role assigned to user", user_id=user_id, role=role_name.value)

        return user

    async def remove_role_from_user(self, user_id: str, role_name: UserRole) -> User:
        """Remove a role from a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundError(user_id)

        role = await self.get_role_by_name(role_name)
        if role and role in user.roles:
            user.roles.remove(role)
            await self._session.flush()
            await self._session.refresh(user)
            logger.info("Role removed from user", user_id=user_id, role=role_name.value)

        return user

    # Permission operations
    async def get_permission_by_name(self, name: Permission) -> Optional[PermissionModel]:
        """Get a permission by name."""
        result = await self._session.execute(
            select(PermissionModel).where(PermissionModel.name == name)
        )
        return result.scalar_one_or_none()

    async def get_permission_by_id(self, permission_id: str) -> Optional[PermissionModel]:
        """Get a permission by ID."""
        result = await self._session.execute(
            select(PermissionModel).where(PermissionModel.id == permission_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_permission(self, name: Permission, description: Optional[str] = None) -> PermissionModel:
        """Get an existing permission or create a new one."""
        permission = await self.get_permission_by_name(name)
        if not permission:
            permission = PermissionModel(name=name, description=description)
            self._session.add(permission)
            await self._session.flush()
            await self._session.refresh(permission)
            logger.info("Permission created", permission_id=permission.id, name=name.value)
        return permission

    async def list_permissions(self) -> List[PermissionModel]:
        """List all permissions."""
        result = await self._session.execute(select(PermissionModel))
        return list(result.scalars().all())

    async def assign_permission_to_role(self, role_name: UserRole, permission_name: Permission) -> Role:
        """Assign a permission to a role."""
        role = await self.get_role_by_name(role_name)
        if not role:
            raise RoleNotFoundError(role_name.value)

        permission = await self.get_or_create_permission(permission_name)
        if permission not in role.permissions:
            role.permissions.append(permission)
            await self._session.flush()
            await self._session.refresh(role)
            logger.info("Permission assigned to role", role=role_name.value, permission=permission_name.value)

        return role

    # Permission checking
    async def user_has_permission(self, user_id: str, permission: Permission) -> bool:
        """Check if a user has a specific permission."""
        user = await self.get_user_by_id(user_id)
        if not user or not user.is_active:
            return False

        user_permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                user_permissions.add(perm.name)

        return permission in user_permissions

    async def user_has_role(self, user_id: str, role_name: UserRole) -> bool:
        """Check if a user has a specific role."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        return any(role.name == role_name for role in user.roles)

    async def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """Get all permissions for a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return set()

        permissions = set()
        for role in user.roles:
            for perm in role.permissions:
                permissions.add(perm.name)

        return permissions

    async def get_user_roles(self, user_id: str) -> List[UserRole]:
        """Get all roles for a user."""
        user = await self.get_user_by_id(user_id)
        if not user:
            return []

        return [role.name for role in user.roles]