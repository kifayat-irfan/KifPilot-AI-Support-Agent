from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.database.models import (
    Organization,
    OrganizationSettings,
    User,
    OrganizationRole,
    OrganizationMember,
)
from app.services.multitenant.exceptions import (
    OrganizationNotFoundError,
    OrganizationAlreadyExistsError,
    OrganizationCreationError,
    OrganizationDeletionError,
    MemberNotFoundError,
    MemberAlreadyExistsError,
    MemberRoleError,
    SettingsNotFoundError,
    OrganizationInactiveError,
)
from app.core.logging import get_logger

logger = get_logger(__name__)


class MultiTenantRepository:
    """Repository for multi-tenant database operations."""

    def __init__(self, session: AsyncSession):
        self._session = session

    # Organization operations
    async def create_organization(
        self,
        name: str,
        slug: str,
        description: Optional[str] = None,
    ) -> Organization:
        """Create a new organization with default settings."""
        try:
            # Check if slug already exists
            existing = await self.get_organization_by_slug(slug)
            if existing:
                raise OrganizationAlreadyExistsError("slug", slug)

            org = Organization(
                name=name,
                slug=slug,
                description=description,
                is_active=True,
            )
            self._session.add(org)
            await self._session.flush()

            # Create default settings
            settings = OrganizationSettings(organization_id=org.id)
            self._session.add(settings)

            await self._session.flush()
            await self._session.refresh(org)

            logger.info("Organization created", organization_id=org.id, slug=slug)
            return org
        except OrganizationAlreadyExistsError:
            raise
        except Exception as e:
            logger.error("Failed to create organization", error=str(e))
            raise OrganizationCreationError(str(e))

    async def get_organization(self, organization_id: str) -> Organization:
        """Get an organization by ID."""
        result = await self._session.execute(
            select(Organization)
            .where(Organization.id == organization_id)
            .options(selectinload(Organization.settings))
        )
        org = result.scalar_one_or_none()
        if not org:
            raise OrganizationNotFoundError(organization_id)
        return org

    async def get_organization_by_slug(self, slug: str) -> Optional[Organization]:
        """Get an organization by slug."""
        result = await self._session.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_organization_with_members(
        self, organization_id: str
    ) -> Organization:
        """Get an organization with members loaded."""
        result = await self._session.execute(
            select(Organization)
            .where(Organization.id == organization_id)
            .options(
                selectinload(Organization.members),
                selectinload(Organization.settings),
            )
        )
        org = result.scalar_one_or_none()
        if not org:
            raise OrganizationNotFoundError(organization_id)
        return org

    async def list_organizations(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[Organization], int]:
        """List organizations with pagination."""
        query = select(Organization)
        if is_active is not None:
            query = query.where(Organization.is_active == is_active)

        # Count total
        count_query = select(func.count(Organization.id))
        if is_active is not None:
            count_query = count_query.where(Organization.is_active == is_active)
        count_result = await self._session.execute(count_query)
        total = count_result.scalar() or 0

        # Get paginated results
        offset = (page - 1) * page_size
        result = await self._session.execute(
            query.order_by(Organization.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        organizations = list(result.scalars().all())

        return organizations, total

    async def update_organization(
        self,
        organization_id: str,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Organization:
        """Update an organization."""
        org = await self.get_organization(organization_id)

        if slug is not None and slug != org.slug:
            existing = await self.get_organization_by_slug(slug)
            if existing and existing.id != organization_id:
                raise OrganizationAlreadyExistsError("slug", slug)
            org.slug = slug

        if name is not None:
            org.name = name
        if description is not None:
            org.description = description
        if is_active is not None:
            org.is_active = is_active

        org.updated_at = datetime.utcnow()
        await self._session.flush()
        await self._session.refresh(org)

        logger.info("Organization updated", organization_id=organization_id)
        return org

    async def delete_organization(self, organization_id: str) -> None:
        """Delete an organization and all its data."""
        try:
            org = await self.get_organization(organization_id)
            await self._session.delete(org)
            await self._session.flush()
            logger.info("Organization deleted", organization_id=organization_id)
        except OrganizationNotFoundError:
            raise
        except Exception as e:
            logger.error("Failed to delete organization", organization_id=organization_id, error=str(e))
            raise OrganizationDeletionError(organization_id, str(e))

    # Member operations
    async def add_member(
        self,
        organization_id: str,
        user_id: str,
        role: OrganizationRole = OrganizationRole.MEMBER,
    ) -> Organization:
        """Add a user to an organization."""
        org = await self.get_organization(organization_id)

        # Check if user exists
        user_result = await self._session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise MemberNotFoundError(organization_id, user_id)

        # Check if already a member
        member_result = await self._session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        if member_result.scalar_one_or_none():
            raise MemberAlreadyExistsError(organization_id, user_id)

        # Add member
        member = OrganizationMember(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )
        self._session.add(member)
        await self._session.flush()

        logger.info("Member added", organization_id=organization_id, user_id=user_id, role=role.value)
        return org

    async def remove_member(self, organization_id: str, user_id: str) -> Organization:
        """Remove a user from an organization."""
        org = await self.get_organization(organization_id)

        result = await self._session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise MemberNotFoundError(organization_id, user_id)

        # Prevent removing the last owner
        if member.role == OrganizationRole.OWNER:
            owner_count_result = await self._session.execute(
                select(func.count(OrganizationMember.user_id)).where(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.role == OrganizationRole.OWNER,
                )
            )
            owner_count = owner_count_result.scalar() or 0
            if owner_count <= 1:
                raise MemberRoleError("Cannot remove the last owner of the organization")

        await self._session.delete(member)
        await self._session.flush()

        logger.info("Member removed", organization_id=organization_id, user_id=user_id)
        return org

    async def update_member_role(
        self,
        organization_id: str,
        user_id: str,
        role: OrganizationRole,
    ) -> Organization:
        """Update a member's role in an organization."""
        org = await self.get_organization(organization_id)

        result = await self._session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            raise MemberNotFoundError(organization_id, user_id)

        # Prevent demoting the last owner
        if member.role == OrganizationRole.OWNER and role != OrganizationRole.OWNER:
            owner_count_result = await self._session.execute(
                select(func.count(OrganizationMember.user_id)).where(
                    OrganizationMember.organization_id == organization_id,
                    OrganizationMember.role == OrganizationRole.OWNER,
                )
            )
            owner_count = owner_count_result.scalar() or 0
            if owner_count <= 1:
                raise MemberRoleError("Cannot demote the last owner of the organization")

        member.role = role
        await self._session.flush()

        logger.info("Member role updated", organization_id=organization_id, user_id=user_id, role=role.value)
        return org

    async def get_member(self, organization_id: str, user_id: str) -> Optional[OrganizationMember]:
        """Get a specific member."""
        result = await self._session.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_members(self, organization_id: str) -> List[OrganizationMember]:
        """List all members of an organization."""
        await self.get_organization(organization_id)  # Verify org exists

        result = await self._session.execute(
            select(OrganizationMember)
            .where(OrganizationMember.organization_id == organization_id)
            .options(selectinload(OrganizationMember.user))
        )
        return list(result.scalars().all())

    async def get_user_organizations(self, user_id: str) -> List[Organization]:
        """Get all organizations a user belongs to."""
        result = await self._session.execute(
            select(Organization)
            .join(OrganizationMember, Organization.id == OrganizationMember.organization_id)
            .where(OrganizationMember.user_id == user_id)
            .options(selectinload(Organization.settings))
        )
        return list(result.scalars().all())

    async def get_user_organization_role(
        self, user_id: str, organization_id: str
    ) -> Optional[OrganizationRole]:
        """Get a user's role in an organization."""
        member = await self.get_member(organization_id, user_id)
        return member.role if member else None

    # Settings operations
    async def get_settings(self, organization_id: str) -> OrganizationSettings:
        """Get organization settings."""
        org = await self.get_organization(organization_id)
        if not org.settings:
            # Create default settings if not exist
            settings = OrganizationSettings(organization_id=organization_id)
            self._session.add(settings)
            await self._session.flush()
            await self._session.refresh(settings)
            return settings
        return org.settings

    async def update_settings(
        self,
        organization_id: str,
        **kwargs,
    ) -> OrganizationSettings:
        """Update organization settings."""
        settings = await self.get_settings(organization_id)

        for key, value in kwargs.items():
            if hasattr(settings, key) and value is not None:
                setattr(settings, key, value)

        settings.updated_at = datetime.utcnow()
        await self._session.flush()
        await self._session.refresh(settings)

        logger.info("Organization settings updated", organization_id=organization_id)
        return settings

    # Validation
    async def validate_organization_access(
        self, user_id: str, organization_id: str
    ) -> bool:
        """Validate that a user has access to an organization."""
        member = await self.get_member(organization_id, user_id)
        return member is not None

    async def validate_organization_active(self, organization_id: str) -> bool:
        """Validate that an organization is active."""
        org = await self.get_organization(organization_id)
        return org.is_active

    async def get_organization_for_resource(
        self, resource_organization_id: str, user_id: str
    ) -> Organization:
        """Get organization and validate user access (for cross-tenant checks)."""
        org = await self.get_organization(resource_organization_id)
        has_access = await self.validate_organization_access(user_id, resource_organization_id)
        if not has_access:
            from app.services.multitenant.exceptions import CrossTenantAccessError
            raise CrossTenantAccessError(resource_organization_id, user_id, "resource")
        if not org.is_active:
            raise OrganizationInactiveError(resource_organization_id)
        return org