from typing import Optional, Callable
from functools import wraps
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.auth.dependencies import get_current_active_user
from app.services.multitenant import MultiTenantService
from app.services.multitenant.repository import MultiTenantRepository
from app.services.multitenant.exceptions import (
    CrossTenantAccessError,
    OrganizationInactiveError,
    OrganizationNotFoundError,
)
from app.database.models import User, OrganizationRole

async def get_multitenant_service(db: AsyncSession = Depends(get_db_session)) -> MultiTenantService:
    """Get multi-tenant service instance."""
    return MultiTenantService(db)


async def get_multitenant_repo(db: AsyncSession = Depends(get_db_session)) -> MultiTenantRepository:
    """Get multi-tenant repository instance."""
    return MultiTenantRepository(db)


async def get_current_organization_id(
    x_organization_id: Optional[str] = Header(None, alias="X-Organization-ID"),
    current_user: User = Depends(get_current_active_user),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
) -> str:
    """
    Get the current organization ID from header or user's default organization.
    
    The X-Organization-ID header takes precedence. If not provided,
    the user's first organization is used.
    """
    if x_organization_id:
        # Validate user has access to this organization
        try:
            await multitenant_service.validate_user_organization(
                current_user.id, x_organization_id
            )
            return x_organization_id
        except (CrossTenantAccessError, OrganizationInactiveError, OrganizationNotFoundError) as e:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"error": e.message, "code": e.code},
            )
    
    # Get user's first organization
    orgs = await multitenant_service.get_user_organizations(current_user.id)
    if not orgs:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "User does not belong to any organization", "code": "NO_ORGANIZATION"},
        )
    
    return orgs[0].id


async def get_current_organization(
    organization_id: str = Depends(get_current_organization_id),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
) -> "Organization":
    """Get the current organization object."""
    from app.database.models import Organization
    org = await multitenant_service._repo.get_organization(organization_id)
    return org


async def require_organization_owner(
    current_user: User = Depends(get_current_active_user),
    organization_id: str = Depends(get_current_organization_id),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
) -> User:
    """Require the current user to be an owner of the organization."""
    role = await multitenant_service.get_user_role_in_org(current_user.id, organization_id)
    if role != OrganizationRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Organization owner required", "code": "OWNER_REQUIRED"},
        )
    return current_user


async def require_organization_admin(
    current_user: User = Depends(get_current_active_user),
    organization_id: str = Depends(get_current_organization_id),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
) -> User:
    """Require the current user to be an admin or owner of the organization."""
    role = await multitenant_service.get_user_role_in_org(current_user.id, organization_id)
    if role not in (OrganizationRole.OWNER, OrganizationRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Organization admin required", "code": "ADMIN_REQUIRED"},
        )
    return current_user


async def require_organization_member(
    current_user: User = Depends(get_current_active_user),
    organization_id: str = Depends(get_current_organization_id),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
) -> User:
    """Require the current user to be a member of the organization."""
    role = await multitenant_service.get_user_role_in_org(current_user.id, organization_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "Not a member of this organization", "code": "NOT_MEMBER"},
        )
    return current_user


def require_organization_role(*roles: OrganizationRole) -> Callable:
    """Dependency to require a specific organization role."""
    async def role_checker(
        current_user: User = Depends(get_current_active_user),
        organization_id: str = Depends(get_current_organization_id),
        multitenant_service: MultiTenantService = Depends(get_multitenant_service),
    ) -> User:
        user_role = await multitenant_service.get_user_role_in_org(current_user.id, organization_id)
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": f"Organization role required: {[r.value for r in roles]}",
                    "code": "ORG_ROLE_REQUIRED",
                },
            )
        return current_user
    return role_checker


# Convenience dependencies
require_org_owner = require_organization_role(OrganizationRole.OWNER)
require_org_admin = require_organization_role(OrganizationRole.OWNER, OrganizationRole.ADMIN)
require_org_member = require_organization_role(
    OrganizationRole.OWNER, OrganizationRole.ADMIN, OrganizationRole.MEMBER
)