import pytest
from httpx import AsyncClient
from app.database.models import UserRole, Permission


class TestRBAC:
    @pytest.mark.asyncio
    async def test_permission_denied_for_viewer(self, client: AsyncClient, test_organization):
        # Create a viewer user
        from app.core.security import hash_password
        from app.database.models import User
        from app.core.database import get_db_session
        from app.services.auth.repository import AuthRepository
        
        async for session in get_db_session():
            viewer = User(
                email="viewer@example.com",
                username="vieweruser",
                hashed_password=hash_password("password123"),
                full_name="Viewer User",
                organization_id=test_organization.id,
                is_active=True,
                is_verified=True,
            )
            session.add(viewer)
            await session.commit()
            await session.refresh(viewer)
            
            auth_repo = AuthRepository(session)
            viewer_role = await auth_repo.get_role_by_name(UserRole.VIEWER)
            if viewer_role:
                await auth_repo.assign_role_to_user(viewer.id, viewer_role.id)
            
            viewer_id = viewer.id
            break
        
        # Login as viewer
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "viewer@example.com", "password": "password123"},
        )
        assert login_resp.status_code == 200
        viewer_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        
        # Try to upload document (should fail)
        response = await client.post(
            "/api/v1/documents/upload",
            headers=viewer_headers,
            files={"file": ("test.txt", b"test content", "text/plain")},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_editor_can_upload(self, client: AsyncClient, test_organization):
        # Create an editor user
        from app.core.security import hash_password
        from app.database.models import User
        from app.core.database import get_db_session
        from app.services.auth.repository import AuthRepository
        
        async for session in get_db_session():
            editor = User(
                email="editor@example.com",
                username="editoruser",
                hashed_password=hash_password("password123"),
                full_name="Editor User",
                organization_id=test_organization.id,
                is_active=True,
                is_verified=True,
            )
            session.add(editor)
            await session.commit()
            await session.refresh(editor)
            
            auth_repo = AuthRepository(session)
            editor_role = await auth_repo.get_role_by_name(UserRole.EDITOR)
            if editor_role:
                await auth_repo.assign_role_to_user(editor.id, editor_role.id)
            
            editor_id = editor.id
            break
        
        # Login as editor
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "editor@example.com", "password": "password123"},
        )
        assert login_resp.status_code == 200
        editor_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        
        # Try to upload document (should succeed with valid file)
        response = await client.post(
            "/api/v1/documents/upload",
            headers=editor_headers,
            files={"file": ("test.txt", b"test content", "text/plain")},
        )
        # Should not be 403 (permission denied)
        assert response.status_code != 403

    @pytest.mark.asyncio
    async def test_admin_has_all_permissions(self, client: AsyncClient, admin_headers):
        # Admin should be able to do everything
        response = await client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200
        
        response = await client.get("/api/v1/organizations", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_manager_can_manage_users(self, client: AsyncClient, test_organization):
        from app.core.security import hash_password
        from app.database.models import User
        from app.core.database import get_db_session
        from app.services.auth.repository import AuthRepository
        
        async for session in get_db_session():
            manager = User(
                email="manager@example.com",
                username="manageruser",
                hashed_password=hash_password("password123"),
                full_name="Manager User",
                organization_id=test_organization.id,
                is_active=True,
                is_verified=True,
            )
            session.add(manager)
            await session.commit()
            await session.refresh(manager)
            
            auth_repo = AuthRepository(session)
            manager_role = await auth_repo.get_role_by_name(UserRole.MANAGER)
            if manager_role:
                await auth_repo.assign_role_to_user(manager.id, manager_role.id)
            
            manager_id = manager.id
            break
        
        login_resp = await client.post(
            "/api/v1/auth/login",
            json={"email": "manager@example.com", "password": "password123"},
        )
        assert login_resp.status_code == 200
        manager_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
        
        # Manager should be able to list users
        response = await client.get("/api/v1/users", headers=manager_headers)
        assert response.status_code == 200