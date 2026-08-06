from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.multitenant.repository import MultiTenantRepository
from app.services.multitenant.schemas import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationListResponse,
    OrganizationMemberAdd,
    OrganizationMemberResponse,
    OrganizationSettingsUpdate,
    OrganizationSettingsResponse,
    OrganizationWithMembers,
)
from app.services.multitenant.exceptions import (
    OrganizationNotFoundError,
    OrganizationCreationError,
    OrganizationDeletionError,
    MemberNotFoundError,
    MemberAlreadyExistsError,
    CrossTenantAccessError,
    OrganizationInactiveError,
    SettingsNotFoundError,
)
from app.database.models import User, OrganizationRole
from app.core.logging import get_logger

logger = get_logger(__name__)


class MultiTenantService:
    """Main multi-tenant service."""

    def __init__(self, session: AsyncSession):
        self._session = session
        self._repo = MultiTenantRepository(session)

    # Organization CRUD
    async def create_organization(self, request: OrganizationCreate) -> OrganizationResponse:
        """Create a new organization."""
        org = await self._repo.create_organization(
            name=request.name,
            slug=request.slug,
            description=request.description,
        )
        # Add creator as owner
        # This would be called from the API after authentication
        return OrganizationResponse.model_validate(org)

    async def get_organization(self, organization_id: str) -> OrganizationResponse:
        """Get an organization by ID."""
        org = await self._repo.get_organization(organization_id)
        return OrganizationResponse.model_validate(org)

    async def get_organization_with_details(
        self, organization_id: str
    ) -> OrganizationWithMembers:
        """Get an organization with members and settings."""
        org = await self._repo.get_organization_with_members(organization_id)
        
        # Convert to response with members
        members = [
            OrganizationMemberResponse(
                user_id=m.user.id,
                username=m.user.username,
                email=m.user.email,
                role=m.role,
                joined_at=m.joined_at,
            )
            for m in org.members
        ]
        
        settings = None
        if org.settings:
            settings = OrganizationSettingsResponse.model_validate(org.settings)
        
        return OrganizationWithMembers(
            **OrganizationResponse.model_validate(org).model_dump(),
            members=members,
            settings=settings,
        )

    async def list_organizations(
        self,
        page: int = 1,
        page_size: int = 20,
        is_active: Optional[bool] = None,
    ) -> OrganizationListResponse:
        """List organizations with pagination."""
        organizations, total = await self._repo.list_organizations(
            page=page,
            page_size=page_size,
            is_active=is_active,
        )
        
        # Add member count to each organization
        org_responses = []
        for org in organizations:
            member_count = len(org.members) if org.members else 0
            org_resp = OrganizationResponse.model_validate(org)
            org_resp.member_count = member_count
            org_responses.append(org_resp)
        
        return OrganizationListResponse(
            organizations=org_responses,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def update_organization(
        self, organization_id: str, request: OrganizationUpdate
    ) -> OrganizationResponse:
        """Update an organization."""
        org = await self._repo.update_organization(
            organization_id=organization_id,
            name=request.name,
            slug=request.slug,
            description=request.description,
            is_active=request.is_active,
        )
        return OrganizationResponse.model_validate(org)

    async def delete_organization(self, organization_id: str) -> None:
        """Delete an organization."""
        await self._repo.delete_organization(organization_id)

    # Member management
    async def add_member(
        self,
        organization_id: str,
        request: OrganizationMemberAdd,
        current_user_id: str,
    ) -> OrganizationMemberResponse:
        """Add a member to an organization."""
        # Check if current user has permission (owner or admin)
        current_role = await self._repo.get_user_organization_role(
            current_user_id, organization_id
        )
        if current_role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
            raise MemberRoleError("Only owners and admins can add members")

        org = await self._repo.add_member(
            organization_id=organization_id,
            user_id=request.user_id,
            role=request.role,
        )

        # Get the member with user details
        member = await self._repo.get_member(organization_id, request.user_id)
        return OrganizationMemberResponse(
            user_id=member.user.id,
            username=member.user.username,
            email=member.user.email,
            role=member.role,
            joined_at=member.joined_at,
        )

    async def remove_member(
        self,
        organization_id: str,
        user_id: str,
        current_user_id: str,
    ) -> None:
        """Remove a member from an organization."""
        # Check permissions
        current_role = await self._repo.get_user_organization_role(
            current_user_id, organization_id
        )
        if current_role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
            raise MemberRoleError("Only owners and admins can remove members")

        # Cannot remove yourself if you're the last owner
        if user_id == current_user_id:
            current_member = await self._repo.get_member(organization_id, user_id)
            if current_member and current_member.role == OrganizationRole.OWNER:
                owner_count = sum(
                    1 for m in await self._repo.list_members(organization_id)
                    if m.role == OrganizationRole.OWNER
                )
                if owner_count <= 1:
                    raise MemberRoleError("Cannot remove yourself as the last owner")

        await self._repo.remove_member(organization_id, user_id)

    async def update_member_role(
        self,
        organization_id: str,
        user_id: str,
        role: OrganizationRole,
        current_user_id: str,
    ) -> OrganizationMemberResponse:
        """Update a member's role."""
        # Only owners can change roles
        current_role = await self._repo.get_user_organization_role(
            current_user_id, organization_id
        )
        if current_role != OrganizationRole.OWNER:
            raise MemberRoleError("Only owners can change member roles")

        org = await self._repo.update_member_role(
            organization_id=organization_id,
            user_id=user_id,
            role=role,
        )

        member = await self._repo.get_member(organization_id, user_id)
        return OrganizationMemberResponse(
            user_id=member.user.id,
            username=member.user.username,
            email=member.user.email,
            role=member.role,
            joined_at=member.joined_at,
        )

    async def list_members(
        self, organization_id: str, current_user_id: str
    ) -> List[OrganizationMemberResponse]:
        """List all members of an organization."""
        await self._validate_access(organization_id, current_user_id)
        members = await self._repo.list_members(organization_id)
        
        return [
            OrganizationMemberResponse(
                user_id=m.user.id,
                username=m.user.username,
                email=m.user.email,
                role=m.role,
                joined_at=m.joined_at,
            )
            for m in members
        ]

    # Settings
    async def get_settings(
        self, organization_id: str, current_user_id: str
    ) -> OrganizationSettingsResponse:
        """Get organization settings."""
        await self._validate_access(organization_id, current_user_id)
        settings = await self._repo.get_settings(organization_id)
        return OrganizationSettingsResponse.model_validate(settings)

    async def update_settings(
        self,
        organization_id: str,
        request: OrganizationSettingsUpdate,
        current_user_id: str,
    ) -> OrganizationSettingsResponse:
        """Update organization settings."""
        # Only owners and admins can update settings
        current_role = await self._repo.get_user_organization_role(
            current_user_id, organization_id
        )
        if current_role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
            from app.services.multitenant.exceptions import MemberRoleError
            raise MemberRoleError("Only owners and admins can update settings")

        settings = await self._repo.update_settings(
            organization_id=organization_id,
            **request.model_dump(exclude_unset=True),
        )
        return OrganizationSettingsResponse.model_validate(settings)

    # Validation helpers
    async def _validate_access(self, organization_id: str, user_id: str) -> None:
        """Validate user has access to organization."""
        org = await self._repo.get_organization_for_resource(organization_id, user_id)
        return org

    async def validate_user_organization(
        self, user_id: str, organization_id: str
    ) -> Organization:
        """Validate user belongs to organization and return it."""
        return await self._repo.get_organization_for_resource(organization_id, user_id)

    async def get_user_organizations(self, user_id: str) -> List[OrganizationResponse]:
        """Get all organizations a user belongs to."""
        orgs = await self._repo.get_user_organizations(user_id)
        return [OrganizationResponse.model_validate(org) for org in orgs]

    async def get_user_role_in_org(
        self, user_id: str, organization_id: str
    ) -> Optional[OrganizationRole]:
        """Get user's role in an organization."""
        return await self._repo.get_user_organization_role(user_id, organization_id)

    # Context for other services
    def get_organization_context(self, organization_id: str) -> Dict[str, Any]:
        """Get context dict for use in other services."""
        return {
            "organization_id": organization_id,
            "vector_collection_name": f"kifpilot_org_{organization_id}",
        }