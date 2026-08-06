from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.services.auth import (
    AuthService,
    LoginRequest,
    RegisterRequest,
    RefreshTokenRequest,
    Token,
    UserResponse,
    UserUpdate,
    RoleResponse,
    PermissionResponse,
    get_current_active_user,
    require_admin,
    require_manage_users,
)
from app.services.auth.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
    InvalidTokenError,
)
from app.database.models import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Register a new user."""
    try:
        user = await auth_service.register(request)
        return user
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": e.message, "code": e.code},
        )


@router.post("/login", response_model=Token)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Authenticate a user and return access and refresh tokens."""
    try:
        token = await auth_service.login(request)
        return token
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": e.message, "code": e.code},
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: RefreshTokenRequest,
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Refresh access token using refresh token."""
    try:
        token = await auth_service.refresh_token(request.refresh_token)
        return token
    except (InvalidTokenError, UserNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": e.message, "code": e.code},
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user),
):
    """Get current authenticated user information."""
    return UserResponse.model_validate(current_user)


@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    request: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Update current user profile."""
    try:
        user = await auth_service.update_user(current_user.id, request)
        return user
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Logout the current user."""
    await auth_service.logout(current_user.id)
    return {"message": "Logged out successfully"}


# Admin routes for user management
@router.get("/users", response_model=list[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """List all users (requires manage_users permission)."""
    users = await auth_service.list_users(skip=skip, limit=limit)
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Get a user by ID (requires manage_users permission)."""
    try:
        user = await auth_service.get_current_user(user_id)
        return user
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    request: UserUpdate,
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Update a user (requires manage_users permission)."""
    try:
        user = await auth_service.update_user(user_id, request)
        return user
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    current_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Delete a user (requires admin role)."""
    try:
        await auth_service.delete_user(user_id)
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )


@router.post("/users/{user_id}/roles/{role_name}", response_model=UserResponse)
async def assign_role_to_user(
    user_id: str,
    role_name: str,
    current_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Assign a role to a user (requires admin role)."""
    try:
        from app.database.models import UserRole
        role = UserRole(role_name)
        user = await auth_service.assign_role(user_id, role)
        return user
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid role: {role_name}", "code": "INVALID_ROLE"},
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )


@router.delete("/users/{user_id}/roles/{role_name}", response_model=UserResponse)
async def remove_role_from_user(
    user_id: str,
    role_name: str,
    current_user: User = Depends(require_admin),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """Remove a role from a user (requires admin role)."""
    try:
        from app.database.models import UserRole
        role = UserRole(role_name)
        user = await auth_service.remove_role(user_id, role)
        return user
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Invalid role: {role_name}", "code": "INVALID_ROLE"},
        )
    except UserNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": e.message, "code": e.code},
        )


@router.get("/roles", response_model=list[RoleResponse])
async def list_roles(
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """List all roles (requires manage_users permission)."""
    roles = await auth_service.list_roles()
    return roles


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    current_user: User = Depends(require_manage_users),
    auth_service: AuthService = Depends(lambda db=Depends(get_db_session): AuthService(db)),
):
    """List all permissions (requires manage_users permission)."""
    permissions = await auth_service.list_permissions()
    return permissions