import pytest
from httpx import AsyncClient


class TestOrganizations:
    @pytest.mark.asyncio
    async def test_create_organization(self, client: AsyncClient, admin_headers):
        response = await client.post(
            "/api/v1/organizations",
            headers=admin_headers,
            json={
                "name": "New Organization",
                "slug": "new-org",
                "description": "A new test organization",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Organization"
        assert data["slug"] == "new-org"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_create_organization_duplicate_slug(self, client: AsyncClient, admin_headers):
        response = await client.post(
            "/api/v1/organizations",
            headers=admin_headers,
            json={
                "name": "Another Organization",
                "slug": "test-org",
                "description": "Duplicate slug",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_organizations(self, client: AsyncClient, admin_headers):
        response = await client.get("/api/v1/organizations", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert "organizations" in data
        assert isinstance(data["organizations"], list)
        assert len(data["organizations"]) >= 1

    @pytest.mark.asyncio
    async def test_get_organization(self, client: AsyncClient, admin_headers, test_organization):
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(test_organization.id)
        assert data["name"] == "Test Organization"

    @pytest.mark.asyncio
    async def test_update_organization(self, client: AsyncClient, admin_headers, test_organization):
        response = await client.patch(
            f"/api/v1/organizations/{test_organization.id}",
            headers=admin_headers,
            json={"name": "Updated Organization", "description": "Updated description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Organization"

    @pytest.mark.asyncio
    async def test_delete_organization(self, client: AsyncClient, admin_headers):
        # First create an org to delete
        create_resp = await client.post(
            "/api/v1/organizations",
            headers=admin_headers,
            json={"name": "To Delete", "slug": "to-delete", "description": "Will be deleted"},
        )
        org_id = create_resp.json()["id"]
        
        response = await client.delete(f"/api/v1/organizations/{org_id}", headers=admin_headers)
        assert response.status_code == 200
        
        # Verify it's deleted
        get_resp = await client.get(f"/api/v1/organizations/{org_id}", headers=admin_headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_organization_members(self, client: AsyncClient, admin_headers, test_organization, test_user):
        response = await client.get(
            f"/api/v1/organizations/{test_organization.id}/members", headers=admin_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "members" in data
        assert len(data["members"]) >= 1

    @pytest.mark.asyncio
    async def test_add_organization_member(self, client: AsyncClient, admin_headers, test_organization):
        response = await client.post(
            f"/api/v1/organizations/{test_organization.id}/members",
            headers=admin_headers,
            json={"email": "newmember@example.com", "role": "editor"},
        )
        assert response.status_code == 201

    @pytest.mark.asyncio
    async def test_update_member_role(self, client: AsyncClient, admin_headers, test_organization, test_user):
        response = await client.patch(
            f"/api/v1/organizations/{test_organization.id}/members/{test_user.id}",
            headers=admin_headers,
            json={"role": "viewer"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_remove_organization_member(self, client: AsyncClient, admin_headers, test_organization, test_user):
        response = await client.delete(
            f"/api/v1/organizations/{test_organization.id}/members/{test_user.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200