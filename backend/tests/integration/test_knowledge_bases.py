import pytest
from httpx import AsyncClient


class TestKnowledgeBase:
    @pytest.mark.asyncio
    async def test_create_knowledge_base(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={
                "name": "Test Knowledge Base",
                "description": "A test knowledge base",
                "embedding_model": "nomic-embed-text",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Knowledge Base"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_knowledge_bases(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/knowledge-bases", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "knowledge_bases" in data
        assert isinstance(data["knowledge_bases"], list)

    @pytest.mark.asyncio
    async def test_get_knowledge_base(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={"name": "KB to Get", "description": "Get this KB"},
        )
        kb_id = create_resp.json()["id"]
        
        response = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == kb_id

    @pytest.mark.asyncio
    async def test_update_knowledge_base(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={"name": "KB to Update", "description": "Original"},
        )
        kb_id = create_resp.json()["id"]
        
        response = await client.patch(
            f"/api/v1/knowledge-bases/{kb_id}",
            headers=auth_headers,
            json={"name": "Updated KB", "description": "Updated description"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated KB"

    @pytest.mark.asyncio
    async def test_delete_knowledge_base(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={"name": "KB to Delete", "description": "Will be deleted"},
        )
        kb_id = create_resp.json()["id"]
        
        response = await client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
        assert response.status_code == 200
        
        get_resp = await client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_add_document_to_kb(self, client: AsyncClient, auth_headers):
        # Create KB
        kb_resp = await client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={"name": "KB with Docs", "description": "Has documents"},
        )
        kb_id = kb_resp.json()["id"]
        
        # Upload document
        doc_resp = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("kb_doc.txt", b"Document for KB", "text/plain")},
        )
        doc_id = doc_resp.json()["document_id"]
        
        # Add to KB
        response = await client.post(
            f"/api/v1/knowledge-bases/{kb_id}/documents",
            headers=auth_headers,
            json={"document_ids": [doc_id]},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_remove_document_from_kb(self, client: AsyncClient, auth_headers):
        kb_resp = await client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={"name": "KB Remove Doc", "description": "Test remove"},
        )
        kb_id = kb_resp.json()["id"]
        
        doc_resp = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("remove_me.txt", b"Remove this", "text/plain")},
        )
        doc_id = doc_resp.json()["document_id"]
        
        await client.post(
            f"/api/v1/knowledge-bases/{kb_id}/documents",
            headers=auth_headers,
            json={"document_ids": [doc_id]},
        )
        
        response = await client.delete(
            f"/api/v1/knowledge-bases/{kb_id}/documents/{doc_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_kb_stats(self, client: AsyncClient, auth_headers):
        kb_resp = await client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={"name": "KB Stats", "description": "Get stats"},
        )
        kb_id = kb_resp.json()["id"]
        
        response = await client.get(f"/api/v1/knowledge-bases/{kb_id}/stats", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "document_count" in data
        assert "chunk_count" in data