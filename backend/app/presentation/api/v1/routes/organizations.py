from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.database import get_db_session
from app.services.multitenant import (
    MultiTenantService,
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
    OrganizationListResponse,
    OrganizationMemberAdd,
    OrganizationMemberResponse,
    OrganizationSettingsUpdate,
    OrganizationSettingsResponse,
    OrganizationWithMembers,
    get_multitenant_service,
    require_organization_owner,
    require_organization_admin,
    require_organization_member,
)
from app.services.multitenant.exceptions import (
    OrganizationNotFoundError,
    OrganizationAlreadyExistsError,
    OrganizationCreationError,
    OrganizationDeletionError,
    MemberNotFoundError,
    MemberAlreadyExistsError,
    MemberRoleError,
)
from app.database.models import User

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Organization created successfully"},
        409: {"description": "Organization already exists"},
        500: {"description": "Failed to create organization"},
    },
)
async def create_organization(
    request: OrganizationCreate,
    current_user: User = Depends(get_current_active_user),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """Create a new organization. The creator becomes the owner."""
    try:
        org = await multitenant_service._repo.create_organization(
            name=request.name,
            slug=request.slug,
            description=request.description,
        )
        
        # Add creator as owner
        await multitenant_service._repo.add_member(
            organization_id=org.id,
            user_id=current_user.id,
            role=OrganizationRole.OWNER,
        )
        
        return OrganizationResponse.model_validate(org)
    except OrganizationAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": e.message, "code": e.code},
        )
    except OrganizationCreationError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.message, "code": e.code},
        )


@router.get(
    "",
    response_model=OrganizationListResponse,
    responses={
        200: {"description": "List of organizations"},
        400: {"description": "Invalid pagination parameters"},
    },
)
async def list_organizations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_active_user),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """List organizations the current user belongs to."""
    orgs = await multitenant_service.get_user_organizations(current_user.id)
    
    # Apply filters
    if is_active is not None:
        orgs = [o for o in orgs if o.is_active == is_active]
    
    # Paginate
    total = len(orgs)
    offset = (page - 1) * page_size
    paginated = orgs[offset:offset + page_size]
    
    return OrganizationListResponse(
        organizations=paginated,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{organization_id}",
    response_model=OrganizationWithMembers,
    responses={
        200: {"description": "Organization with members and settings"},
        404: {"description": "Organization not found"},
        403: {"description": "Not a member of this organization"},
    },
)
async def get_organization(
    organization_id: str,
    current_user: User = Depends(require_organization_member),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """Get an organization with members and settings."""
    try:
        return await multitenant_service.get_organization_with_details(organization_id)
    except OrganizationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )


@router.patch(
    "/{organization_id}",
    response_model=OrganizationResponse,
    responses={
        200: {"description": "Organization updated successfully"},
        404: {"description": "Organization not found"},
        409: {"description": "Slug already exists"},
        403: {"description": "Not authorized"},
    },
)
async def update_organization(
    organization_id: str,
    request: OrganizationUpdate,
    current_user: User = Depends(require_organization_admin),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """Update an organization (requires admin or owner)."""
    try:
        return await multitenant_service.update_organization(organization_id, request)
    except OrganizationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )
    except OrganizationAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": e.message, "code": e.code},
        )


@router.delete(
    "/{organization_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Organization deleted successfully"},
        404: {"description": "Organization not found"},
        403: {"description": "Only owner can delete organization"},
    },
)
async def delete_organization(
    organization_id: str,
    current_user: User = Depends(require_organization_owner),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """Delete an organization (requires owner)."""
    try:
        await multitenant_service.delete_organization(organization_id)
    except OrganizationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )
    except OrganizationDeletionError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": e.message, "code": e.code},
        )


# Member management
@router.post(
    "/{organization_id}/members",
    response_model=OrganizationMemberResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Member added successfully"},
        404: {"description": "Organization or user not found"},
        409: {"description": "User already a member"},
        403: {"description": "Not authorized"},
    },
)
async def add_member(
    organization_id: str,
    request: OrganizationMemberAdd,
    current_user: User = Depends(require_organization_admin),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """Add a member to the organization (requires admin or owner)."""
    try:
        return await multitenant_service.add_member(
            organization_id=organization_id,
            request=request,
            current_user_id=current_user.id,
        )
    except OrganizationNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )
    except MemberAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": e.message, "code": e.code},
        )
    except MemberRoleError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": e.message, "code": e.code},
        )


@router.get(
    "/{organization_id}/members",
    response_model=list[OrganizationMemberResponse],
    responses={
        200: {"description": "List of members"},
        403: {"description": "Not a member of this organization"},
    },
)
async def list_members(
    organization_id: str,
    current_user: User = Depends(require_organization_member),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """List all members of the organization."""
    return await multitenant_service.list_members(organization_id, current_user.id)


@router.delete(
    "/{organization_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Member removed successfully"},
        404: {"description": "Member not found"},
        403: {"description": "Not authorized"},
    },
)
async def remove_member(
    organization_id: str,
    user_id: str,
    current_user: User = Depends(require_organization_admin),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """Remove a member from the organization (requires admin or owner)."""
    try:
        await multitenant_service.remove_member(
            organization_id=organization_id,
            user_id=user_id,
            current_user_id=current_user.id,
        )
    except MemberNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )
    except MemberRoleError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": e.message, "code": e.code},
        )


@router.patch(
    "/{organization_id}/members/{user_id}/role",
    response_model=OrganizationMemberResponse,
    responses={
        200: {"description": "Member role updated successfully"},
        404: {"description": "Member not found"},
        403: {"description": "Only owner can change roles"},
    },
)
async def update_member_role(
    organization_id: str,
    user_id: str,
    role: str,
    current_user: User = Depends(require_organization_owner),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """Update a member's role (requires owner)."""
    try:
        from app.database.models import OrganizationRole
        role_enum = OrganizationRole(role)
        return await multitenant_service.update_member_role(
            organization_id=organization_id,
            user_id=user_id,
            role=role_enum,
            current_user_id=current_user.id,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid role: {role}", "code": "INVALID_ROLE"},
        )
    except MemberNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )
    except MemberRoleError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": e.message, "code": e.code},
        )


# Settings
@router.get(
    "/{organization_id}/settings",
    response_model=OrganizationSettingsResponse,
    responses={
        200: {"description": "Organization settings"},
        403: {"description": "Not a member of this organization"},
    },
)
async def get_settings(
    organization_id: str,
    current_user: User = Depends(require_organization_member),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """Get organization settings."""
    return await multitenant_service.get_settings(organization_id, current_user.id)


@router.patch(
    "/{organization_id}/settings",
    response_model=OrganizationSettingsResponse,
    responses={
        200: {"description": "Settings updated successfully"},
        403: {"description": "Not authorized"},
    },
)
async def update_settings(
    organization_id: str,
    request: OrganizationSettingsUpdate,
    current_user: User = Depends(require_organization_admin),
    multitenant_service: MultiTenantService = Depends(get_multitenant_service),
):
    """Update organization settings (requires admin or owner)."""
    try:
        return await multitenant_service.update_settings(organization_id, request, current_user.id)
    except MemberRoleError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": e.message, "code": e.code},
        )


# Import for current_user dependency
from app.services.auth.dependencies import get_current_active_user