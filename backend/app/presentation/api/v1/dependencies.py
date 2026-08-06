# Re-export auth dependencies for backward compatibility and ease of use
from app.services.auth.dependencies import (
    get_current_user_id,
    get_current_user,
    get_current_active_user,
    require_permission,
    require_role,
    require_any_permission,
    require_any_role,
    require_upload_documents,
    require_delete_documents,
    require_chat,
    require_view_sessions,
    require_manage_users,
    require_manage_settings,
    require_admin,
    require_manager,
    require_editor,
    require_viewer,
)
from app.database.models import User
from fastapi import Depends, HTTPException, status

# Backward compatibility - UserModel alias
UserModel = User

# Get current organization ID from user
async def get_current_organization_id(
    current_user: User = Depends(get_current_active_user),
) -> str:
    """Get current user's organization ID."""
    if not current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is not associated with any organization",
        )
    return current_user.organization_id

__all__ = [
    "get_current_user_id",
    "get_current_user",
    "get_current_active_user",
    "require_permission",
    "require_role",
    "require_any_permission",
    "require_any_role",
    "require_upload_documents",
    "require_delete_documents",
    "require_chat",
    "require_view_sessions",
    "require_manage_users",
    "require_manage_settings",
    "require_admin",
    "require_manager",
    "require_editor",
    "require_viewer",
    "UserModel",
]