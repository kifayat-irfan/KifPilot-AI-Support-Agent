# RBAC Flow

## Overview

Role-Based Access Control with 4 roles, 6 permissions, and organization-scoped enforcement.

## Role Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│                        ADMIN                                 │
│  Permissions: ALL (MANAGE_SETTINGS + MANAGE_USERS + ...)    │
│  Scope: Organization + System                                │
└────────────────────────────┬────────────────────────────────┘
                             │ inherits
┌────────────────────────────▼────────────────────────────────┐
│                       MANAGER                                │
│  Permissions: MANAGE_USERS + EDITOR permissions             │
│  Scope: Organization                                         │
└────────────────────────────┬────────────────────────────────┘
                             │ inherits
┌────────────────────────────▼────────────────────────────────┐
│                       EDITOR                                 │
│  Permissions: UPLOAD_DOCUMENTS, DELETE_DOCUMENTS,           │
│               CHAT, VIEW_SESSIONS                           │
│  Scope: Organization                                         │
└────────────────────────────┬────────────────────────────────┘
                             │ inherits
┌────────────────────────────▼────────────────────────────────┐
│                       VIEWER                                 │
│  Permissions: CHAT, VIEW_SESSIONS                           │
│  Scope: Organization                                         │
└─────────────────────────────────────────────────────────────┘
```

## Permission Matrix

| Permission | Description | Viewer | Editor | Manager | Admin |
|------------|-------------|--------|--------|---------|-------|
| `CHAT` | Use chat/RAG endpoints | ✅ | ✅ | ✅ | ✅ |
| `VIEW_SESSIONS` | View conversation history | ✅ | ✅ | ✅ | ✅ |
| `UPLOAD_DOCUMENTS` | Upload documents to KBs | ❌ | ✅ | ✅ | ✅ |
| `DELETE_DOCUMENTS` | Delete/restore documents | ❌ | ✅ | ✅ | ✅ |
| `MANAGE_USERS` | Invite/remove users, change roles | ❌ | ❌ | ✅ | ✅ |
| `MANAGE_SETTINGS` | Organization settings, integrations | ❌ | ❌ | ❌ | ✅ |

## Database Schema

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    organization_id UUID REFERENCES organizations(id),
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Roles table
CREATE TABLE roles (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE NOT NULL,  -- 'admin', 'manager', 'editor', 'viewer'
    description TEXT,
    is_system BOOLEAN DEFAULT TRUE
);

-- Permissions table
CREATE TABLE permissions (
    id UUID PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,  -- 'UPLOAD_DOCUMENTS', etc.
    description TEXT
);

-- Role-Permission mapping
CREATE TABLE role_permissions (
    role_id UUID REFERENCES roles(id),
    permission_id UUID REFERENCES permissions(id),
    PRIMARY KEY (role_id, permission_id)
);

-- User-Role mapping (per organization)
CREATE TABLE user_roles (
    user_id UUID REFERENCES users(id),
    role_id UUID REFERENCES roles(id),
    organization_id UUID REFERENCES organizations(id),
    assigned_by UUID REFERENCES users(id),
    assigned_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id, organization_id)
);
```

## Role Definitions

```python
# database/models.py
class UserRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    EDITOR = "editor"
    VIEWER = "viewer"

class Permission(str, Enum):
    UPLOAD_DOCUMENTS = "upload_documents"
    DELETE_DOCUMENTS = "delete_documents"
    CHAT = "chat"
    VIEW_SESSIONS = "view_sessions"
    MANAGE_USERS = "manage_users"
    MANAGE_SETTINGS = "manage_settings"

# Default role-permission mapping
DEFAULT_ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.CHAT,
        Permission.VIEW_SESSIONS,
        Permission.MANAGE_USERS,
        Permission.MANAGE_SETTINGS,
    ],
    UserRole.MANAGER: [
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.CHAT,
        Permission.VIEW_SESSIONS,
        Permission.MANAGE_USERS,
    ],
    UserRole.EDITOR: [
        Permission.UPLOAD_DOCUMENTS,
        Permission.DELETE_DOCUMENTS,
        Permission.CHAT,
        Permission.VIEW_SESSIONS,
    ],
    UserRole.VIEWER: [
        Permission.CHAT,
        Permission.VIEW_SESSIONS,
    ],
}
```

## Authorization Flow

```
Request → Extract Token → Verify JWT → Get User → Check Role/Permission → Allow/Deny
   │           │            │          │           │                        │
   ▼           ▼            ▼          ▼           ▼                        ▼
Middleware  Depends()    verify_token  DB Query   require_permission()     403/200
            (oauth2)     (signature,   (user +    (role_permissions +      (JSON)
             scheme)     expiry,      roles)     user_roles join)
             Bearer      type=access)
```

## Dependency Injection

```python
# services/auth/dependencies.py
async def get_current_active_user(
    user_id: str = Depends(get_current_user_id),
    auth_service: AuthService = Depends(get_auth_service)
) -> User:
    user = await auth_service.repo.get_user_by_id(user_id)
    if not user or not user.is_active:
        raise HTTPException(403, "Inactive user")
    return user

def require_permission(permission: Permission):
    async def checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        has_perm = await auth_service.repo.user_has_permission(current_user.id, permission)
        if not has_perm:
            # Audit log
            await audit_logger.log_permission_denied(
                user_id=current_user.id,
                username=current_user.username,
                organization_id=current_user.organization_id,
                resource_type="endpoint",
                resource_id=request.url.path,
                required_permission=permission.value,
                ip_address=request.client.host
            )
            raise HTTPException(403, f"Permission denied: {permission.value}")
        return current_user
    return checker

def require_role(role: UserRole):
    async def checker(
        current_user: User = Depends(get_current_active_user),
        auth_service: AuthService = Depends(get_auth_service)
    ) -> User:
        has_role = await auth_service.repo.user_has_role(current_user.id, role)
        if not has_role:
            raise HTTPException(403, f"Role required: {role.value}")
        return current_user
    return checker

# Convenience dependencies
require_upload_documents = require_permission(Permission.UPLOAD_DOCUMENTS)
require_delete_documents = require_permission(Permission.DELETE_DOCUMENTS)
require_chat = require_permission(Permission.CHAT)
require_view_sessions = require_permission(Permission.VIEW_SESSIONS)
require_manage_users = require_permission(Permission.MANAGE_USERS)
require_manage_settings = require_permission(Permission.MANAGE_SETTINGS)

require_admin = require_role(UserRole.ADMIN)
require_manager = require_any_role(UserRole.ADMIN, UserRole.MANAGER)
require_editor = require_any_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR)
require_viewer = require_any_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.EDITOR, UserRole.VIEWER)
```

## Route Protection

```python
# presentation/api/v1/routes/documents.py
@router.post("/upload", dependencies=[Depends(require_upload_documents)])
async def upload_document(...):
    ...

@router.delete("/{doc_id}", dependencies=[Depends(require_delete_documents)])
async def delete_document(...):
    ...

# presentation/api/v1/routes/chat.py
@router.post("/stream", dependencies=[Depends(require_chat)])
async def stream_chat(...):
    ...

@router.post("/ask", dependencies=[Depends(require_chat)])
async def ask_chat(...):
    ...

# presentation/api/v1/routes/admin.py
@router.get("/users", dependencies=[Depends(require_manage_users)])
async def list_users(...):
    ...

@router.patch("/settings", dependencies=[Depends(require_manage_settings)])
async def update_settings(...):
    ...
```

## Permission Checking Logic

```python
# services/auth/repository.py
class AuthRepository:
    async def user_has_permission(self, user_id: str, permission: Permission) -> bool:
        # Check user roles -> role permissions
        query = """
            SELECT 1 FROM user_roles ur
            JOIN role_permissions rp ON ur.role_id = rp.role_id
            JOIN permissions p ON rp.permission_id = p.id
            WHERE ur.user_id = :user_id AND p.name = :perm
            AND ur.organization_id = (SELECT organization_id FROM users WHERE id = :user_id)
        """
        result = await self.session.execute(query, {"user_id": user_id, "perm": permission.value})
        return result.first() is not None
    
    async def user_has_role(self, user_id: str, role: UserRole) -> bool:
        query = """
            SELECT 1 FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            WHERE ur.user_id = :user_id AND r.name = :role
            AND ur.organization_id = (SELECT organization_id FROM users WHERE id = :user_id)
        """
        result = await self.session.execute(query, {"user_id": user_id, "role": role.value})
        return result.first() is not None
    
    async def assign_role(self, user_id: str, role_id: str, assigned_by: str) -> UserRole:
        # Check assigner has MANAGE_USERS
        # Create user_roles entry
        # Audit log
        ...
    
    async def revoke_role(self, user_id: str, role_id: str) -> bool:
        ...
```

## Organization-Scoped Roles

```python
# Users can have different roles in different organizations
# user_roles table includes organization_id

async def get_user_roles_in_org(self, user_id: str, org_id: str) -> List[UserRole]:
    query = """
        SELECT r.name FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        WHERE ur.user_id = :user_id AND ur.organization_id = :org_id
    """
    result = await self.session.execute(query, {"user_id": user_id, "org_id": org_id})
    return [UserRole(row[0]) for row in result.fetchall()]
```

## Role Assignment Flow

```
Admin/Manager                    System
    │                               │
    ├─ POST /orgs/{id}/members ───► │
    │  { email, role }             │
    │                               ├─ Validate requester has MANAGE_USERS
    │                               ├─ Find/create user by email
    │                               ├─ Check user not already member
    │                               ├─ Create user_roles entry
    │                               ├─ Audit log (role_assigned)
    │                               │
    │ ◄── 201 Created ──────────────┤
    │                               │
```

## Audit Logging for RBAC

```python
await audit_logger.log_role_change(
    actor_user_id=admin.id,
    actor_username=admin.username,
    target_user_id=user.id,
    target_username=user.username,
    organization_id=org_id,
    old_role="viewer",
    new_role="editor",
    ip_address=request.client.host
)

await audit_logger.log_admin_action(
    admin_user_id=admin.id,
    admin_username=admin.username,
    action="assign_role",
    target_type="user",
    target_id=user.id,
    target_name=user.username,
    organization_id=org_id,
    ip_address=request.client.host,
    metadata={"role": "editor"}
)
```

## Testing RBAC

```python
# tests/integration/test_rbac.py
class TestRBAC:
    @pytest.mark.asyncio
    async def test_viewer_cannot_upload(self, client, viewer_headers):
        resp = await client.post("/documents/upload", headers=viewer_headers, files={...})
        assert resp.status_code == 403
    
    @pytest.mark.asyncio
    async def test_editor_can_upload(self, client, editor_headers):
        resp = await client.post("/documents/upload", headers=editor_headers, files={...})
        assert resp.status_code != 403
    
    @pytest.mark.asyncio
    async def test_manager_can_manage_users(self, client, manager_headers):
        resp = await client.get("/users", headers=manager_headers)
        assert resp.status_code == 200
    
    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(self, client, admin_headers):
        for endpoint in ["/users", "/organizations", "/settings"]:
            resp = await client.get(endpoint, headers=admin_headers)
            assert resp.status_code == 200
```