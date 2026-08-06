import pytest
from httpx import AsyncClient


class TestUsers:
    @pytest.mark.asyncio
    async def test_list_users(self, client: AsyncClient, admin_headers):
        response = await client.get("/api/v1/users", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "users" in data
        assert isinstance(data["users"], list)

    @pytest.mark.asyncio
    async def test_get_user(self, client: AsyncClient, admin_headers, test_user):
        response = await client.get(f"/api/v1/users/{test_user.id}", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_user.id)
        assert data["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_update_user(self, client: AsyncClient, admin_headers, test_user):
        response = await client.patch(
            f"/api/v1/users/{test_user.id}",
            headers=admin_headers,
            json={"full_name": "Updated Name", "is_active": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_delete_user(self, client: AsyncClient, admin_headers, test_organization):
        # Create user to delete
        from app.core.security import hash_password
        from app.database.models import User
        from app.core.database import get_db_session
        
        async for session in get_db_session():
            user = User(
                email="todelete@example.com",
                username="todelete",
                hashed_password=hash_password("password123"),
                full_name="To Delete",
                organization_id=test_organization.id,
                is_active=True,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id
            break
        
        response = await client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_roles(self, client: AsyncClient, admin_headers, test_user):
        response = await client.get(f"/api/v1/users/{test_user.id}/roles", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "roles" in data

    @pytest.mark.asyncio
    async def test_assign_role(self, client: AsyncClient, admin_headers, test_user):
        response = await client.post(
            f"/api/v1/users/{test_user.id}/roles",
            headers=admin_headers,
            json={"role": "editor"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_revoke_role(self, client: AsyncClient, admin_headers, test_user):
        # First assign a role
        await client.post(
            f"/api/v1/users/{test_user.id}/roles",
            headers=admin_headers,
            json={"role": "viewer"},
        )
        
        response = await client.delete(
            f"/api/v1/users/{test_user.id}/roles/viewer",
            headers=admin_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_user_permissions(self, client: AsyncClient, admin_headers, test_user):
        response = await client.get(f"/api/v1/users/{test_user.id}/permissions", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "permissions" in data