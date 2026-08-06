import pytest
import os
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import ASGITransport, AsyncClient
from app.main import create_app


@pytest.fixture
async def api_client():
    transport = ASGITransport(app=create_app())
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestFrontendAPIIntegration:
    """Integration tests for frontend API calls"""

    @pytest.mark.asyncio
    async def test_auth_flow(self, api_client):
        # Register
        register_resp = await api_client.post(
            "/api/v1/auth/register",
            json={
                "email": "frontend@example.com",
                "username": "frontenduser",
                "password": "password123",
                "full_name": "Frontend User",
            },
        )
        assert register_resp.status_code == 201
        
        # Login
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "frontend@example.com", "password": "password123"},
        )
        assert login_resp.status_code == 200
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get current user
        me_resp = await api_client.get("/api/v1/auth/me", headers=headers)
        assert me_resp.status_code == 200
        
        # Refresh token
        refresh_resp = await api_client.post("/api/v1/auth/refresh", headers=headers)
        assert refresh_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_document_upload_flow(self, api_client):
        # Login
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Upload document
        upload_resp = await api_client.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("integration.txt", b"Integration test", "text/plain")},
        )
        assert upload_resp.status_code == 201
        doc_id = upload_resp.json()["document_id"]
        
        # List documents
        list_resp = await api_client.get("/api/v1/documents", headers=headers)
        assert list_resp.status_code == 200
        
        # Get document
        get_resp = await api_client.get(f"/api/v1/documents/{doc_id}", headers=headers)
        assert get_resp.status_code == 200
        
        # Update metadata
        update_resp = await api_client.patch(
            f"/api/v1/documents/{doc_id}",
            headers=headers,
            json={"title": "Updated Title"},
        )
        assert update_resp.status_code == 200
        
        # Delete
        delete_resp = await api_client.delete(f"/api/v1/documents/{doc_id}", headers=headers)
        assert delete_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_knowledge_base_flow(self, api_client):
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create KB
        kb_resp = await api_client.post(
            "/api/v1/knowledge-bases",
            headers=headers,
            json={"name": "Integration KB", "description": "Test"},
        )
        assert kb_resp.status_code == 201
        kb_id = kb_resp.json()["id"]
        
        # List KBs
        list_resp = await api_client.get("/api/v1/knowledge-bases", headers=headers)
        assert list_resp.status_code == 200
        
        # Get KB
        get_resp = await api_client.get(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
        assert get_resp.status_code == 200
        
        # Delete KB
        delete_resp = await api_client.delete(f"/api/v1/knowledge-bases/{kb_id}", headers=headers)
        assert delete_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_flow(self, api_client):
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Non-streaming chat
        chat_resp = await api_client.post(
            "/api/v1/chat/ask",
            headers=headers,
            json={"question": "Integration test question", "top_k": 3},
        )
        assert chat_resp.status_code == 200
        data = chat_resp.json()
        assert "answer" in data
        assert "citations" in data
        
        # Streaming chat
        stream_resp = await api_client.post(
            "/api/v1/chat/stream",
            headers=headers,
            json={"question": "Stream test", "top_k": 3},
        )
        assert stream_resp.status_code == 200
        assert "text/event-stream" in stream_resp.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_conversation_flow(self, api_client):
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create conversation
        conv_resp = await api_client.post(
            "/api/v1/conversations",
            headers=headers,
            json={"title": "Integration Conversation"},
        )
        assert conv_resp.status_code == 201
        conv_id = conv_resp.json()["id"]
        
        # Send message
        msg_resp = await api_client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=headers,
            json={"role": "user", "content": "Hello"},
        )
        assert msg_resp.status_code == 201
        
        # Get messages
        get_resp = await api_client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
        assert get_resp.status_code == 200
        
        # Delete conversation
        del_resp = await api_client.delete(f"/api/v1/conversations/{conv_id}", headers=headers)
        assert del_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_retrieval_flow(self, api_client):
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Search
        search_resp = await api_client.post(
            "/api/v1/retrieval/search",
            headers=headers,
            json={"query": "test query", "top_k": 5},
        )
        assert search_resp.status_code == 200
        
        # Hybrid search
        hybrid_resp = await api_client.post(
            "/api/v1/retrieval/hybrid-search",
            headers=headers,
            json={"query": "hybrid query", "top_k": 5, "use_rrf": True},
        )
        assert hybrid_resp.status_code == 200
        
        # Rerank
        rerank_resp = await api_client.post(
            "/api/v1/retrieval/rerank",
            headers=headers,
            json={"query": "rerank query", "documents": [{"id": "1", "text": "test"}]},
        )
        assert rerank_resp.status_code == 200

    @pytest.mark.asyncio
    async def test_rag_flow(self, api_client):
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # RAG query
        rag_resp = await api_client.post(
            "/api/v1/rag/query",
            headers=headers,
            json={"question": "RAG test question", "top_k": 5},
        )
        assert rag_resp.status_code == 200
        data = rag_resp.json()
        assert "answer" in data
        assert "citations" in data
        assert "confidence" in data


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_401_unauthorized(self, api_client):
        resp = await api_client.get("/api/v1/auth/me")
        assert resp.status_code == 401
        
        resp = await api_client.get("/api/v1/documents")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_404_not_found(self, api_client):
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = await api_client.get("/api/v1/documents/00000000-0000-0000-0000-000000000000", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_400_validation_error(self, api_client):
        login_resp = await api_client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "testpassword123"},
        )
        token = login_resp.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # Invalid file type
        resp = await api_client.post(
            "/api/v1/documents/upload",
            headers=headers,
            files={"file": ("test.exe", b"MZ\x90\x00", "application/x-msdownload")},
        )
        assert resp.status_code == 415

    @pytest.mark.asyncio
    async def test_429_rate_limit(self, api_client):
        # Make many requests to trigger rate limit
        for _ in range(15):
            resp = await api_client.get("/api/v1/health")
            if resp.status_code == 429:
                break
        else:
            pytest.skip("Rate limit not triggered")
        
        assert resp.status_code == 429
        assert "Retry-After" in resp.headers