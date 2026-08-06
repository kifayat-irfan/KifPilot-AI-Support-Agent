import pytest
from httpx import AsyncClient
import io


class TestDocuments:
    @pytest.mark.asyncio
    async def test_upload_document(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test.txt", b"Test document content", "text/plain")},
        )
        assert response.status_code == 201
        data = response.json()
        assert "document_id" in data
        assert data["filename"] == "test.txt"

    @pytest.mark.asyncio
    async def test_upload_pdf(self, client: AsyncClient, auth_headers):
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n>>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<<\n/Size 4\n/Root 1 0 R\n>>\nstartxref\n193\n%%EOF"
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test.pdf", pdf_content, "application/pdf")},
        )
        assert response.status_code == 201
        data = response.json()
        assert "document_id" in data

    @pytest.mark.asyncio
    async def test_upload_invalid_file_type(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test.exe", b"MZ\x90\x00", "application/x-msdownload")},
        )
        assert response.status_code == 415

    @pytest.mark.asyncio
    async def test_upload_empty_file(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("empty.txt", b"", "text/plain")},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_documents(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/documents", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert "total" in data
        assert "page" in data

    @pytest.mark.asyncio
    async def test_list_documents_with_filters(self, client: AsyncClient, auth_headers):
        response = await client.get(
            "/api/v1/documents",
            headers=auth_headers,
            params={"category": "test", "page": 1, "page_size": 10},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_document(self, client: AsyncClient, auth_headers):
        # First upload a document
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test.txt", b"Test content for get", "text/plain")},
        )
        doc_id = upload_resp.json()["document_id"]
        
        response = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == doc_id

    @pytest.mark.asyncio
    async def test_update_document_metadata(self, client: AsyncClient, auth_headers):
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("test.txt", b"Test content", "text/plain")},
        )
        doc_id = upload_resp.json()["document_id"]
        
        response = await client.patch(
            f"/api/v1/documents/{doc_id}",
            headers=auth_headers,
            json={"title": "Updated Title", "description": "Updated description", "tags": ["tag1", "tag2"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Updated Title"
        assert "tag1" in data["tags"]

    @pytest.mark.asyncio
    async def test_delete_document(self, client: AsyncClient, auth_headers):
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("todelete.txt", b"Delete me", "text/plain")},
        )
        doc_id = upload_resp.json()["document_id"]
        
        response = await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify deleted
        get_resp = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_restore_document(self, client: AsyncClient, auth_headers):
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("torestore.txt", b"Restore me", "text/plain")},
        )
        doc_id = upload_resp.json()["document_id"]
        
        # Soft delete
        await client.delete(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        
        # Restore
        response = await client.post(f"/api/v1/documents/{doc_id}/restore", headers=auth_headers)
        assert response.status_code == 200
        
        # Verify restored
        get_resp = await client.get(f"/api/v1/documents/{doc_id}", headers=auth_headers)
        assert get_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_get_document_chunks(self, client: AsyncClient, auth_headers):
        upload_resp = await client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("chunks.txt", b"Chunk 1\n\nChunk 2\n\nChunk 3", "text/plain")},
        )
        doc_id = upload_resp.json()["document_id"]
        
        response = await client.get(f"/api/v1/documents/{doc_id}/chunks", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)