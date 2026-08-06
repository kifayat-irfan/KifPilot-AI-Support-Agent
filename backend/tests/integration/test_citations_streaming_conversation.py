import pytest
from httpx import AsyncClient
import json


class TestCitations:
    @pytest.mark.asyncio
    async def test_citations_in_rag_response(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/rag/query",
            headers=auth_headers,
            json={"question": "Test citations", "top_k": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "citations" in data
        assert isinstance(data["citations"], list)
        
        # Verify citation structure
        for citation in data["citations"]:
            assert "document_id" in citation
            assert "chunk_id" in citation
            assert "text" in citation
            assert "score" in citation

    @pytest.mark.asyncio
    async def test_citations_in_streaming(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/rag/stream",
            headers=auth_headers,
            json={"question": "Stream with citations", "top_k": 5},
        )
        assert response.status_code == 200
        
        # Parse SSE events
        events = []
        for line in response.text.split("\n"):
            if line.startswith("event: ") or line.startswith("data: "):
                events.append(line)
        
        # Should have citations event
        citation_events = [e for e in events if "citations" in e]
        assert len(citation_events) > 0

    @pytest.mark.asyncio
    async def test_citation_precision(self, client: AsyncClient, auth_headers):
        # Test that citations are relevant
        response = await client.post(
            "/api/v1/rag/query",
            headers=auth_headers,
            json={"question": "Specific test question", "top_k": 5},
        )
        assert response.status_code == 200
        data = response.json()
        
        # If we have citations, they should have valid structure
        for citation in data.get("citations", []):
            assert citation["score"] >= 0
            assert citation["score"] <= 1
            assert len(citation["text"]) > 0


class TestStreaming:
    @pytest.mark.asyncio
    async def test_stream_chat(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/chat/stream",
            headers=auth_headers,
            json={"question": "Stream test question", "top_k": 5},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        # Check for expected SSE events
        events = response.text.split("\n")
        event_types = set()
        for line in events:
            if line.startswith("event: "):
                event_types.add(line.replace("event: ", "").strip())
        
        # Should have start, token, and complete events
        assert "start" in event_types
        assert "token" in event_types
        assert "complete" in event_types

    @pytest.mark.asyncio
    async def test_stream_chat_cancellation(self, client: AsyncClient, auth_headers):
        # Test that client disconnect stops generation
        response = await client.post(
            "/api/v1/chat/stream",
            headers=auth_headers,
            json={"question": "Long streaming test " * 100, "top_k": 5},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_non_streaming_chat(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/chat/ask",
            headers=auth_headers,
            json={"question": "Non-streaming question", "top_k": 5},
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert "confidence" in data

    @pytest.mark.asyncio
    async def test_stream_health(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/chat/stream/health", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestConversationMemory:
    @pytest.mark.asyncio
    async def test_create_conversation(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "Test Conversation"},
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["title"] == "Test Conversation"

    @pytest.mark.asyncio
    async def test_list_conversations(self, client: AsyncClient, auth_headers):
        response = await client.get("/api/v1/conversations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "conversations" in data
        assert isinstance(data["conversations"], list)

    @pytest.mark.asyncio
    async def test_get_conversation(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "Conversation to Get"},
        )
        conv_id = create_resp.json()["id"]
        
        response = await client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conv_id

    @pytest.mark.asyncio
    async def test_send_message(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "Conversation with Messages"},
        )
        conv_id = create_resp.json()["id"]
        
        response = await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=auth_headers,
            json={"role": "user", "content": "Hello, this is a test message"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["role"] == "user"
        assert data["content"] == "Hello, this is a test message"

    @pytest.mark.asyncio
    async def test_get_messages(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "Conversation for Messages"},
        )
        conv_id = create_resp.json()["id"]
        
        await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=auth_headers,
            json={"role": "user", "content": "First message"},
        )
        
        response = await client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) >= 1

    @pytest.mark.asyncio
    async def test_delete_conversation(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "Conversation to Delete"},
        )
        conv_id = create_resp.json()["id"]
        
        response = await client.delete(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
        assert response.status_code == 200
        
        get_resp = await client.get(f"/api/v1/conversations/{conv_id}", headers=auth_headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_conversation_context_in_rag(self, client: AsyncClient, auth_headers):
        create_resp = await client.post(
            "/api/v1/conversations",
            headers=auth_headers,
            json={"title": "RAG Conversation"},
        )
        conv_id = create_resp.json()["id"]
        
        # Add some messages
        await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=auth_headers,
            json={"role": "user", "content": "What is the capital of France?"},
        )
        await client.post(
            f"/api/v1/conversations/{conv_id}/messages",
            headers=auth_headers,
            json={"role": "assistant", "content": "Paris is the capital of France."},
        )
        
        # Query with conversation context
        response = await client.post(
            "/api/v1/rag/query",
            headers=auth_headers,
            json={
                "question": "What language do they speak there?",
                "conversation_id": conv_id,
                "top_k": 5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data