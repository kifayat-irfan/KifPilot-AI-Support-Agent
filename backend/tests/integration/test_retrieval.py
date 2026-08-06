import pytest
from httpx import AsyncClient


class TestRetrieval:
    @pytest.mark.asyncio
    async def test_search(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/retrieval/search",
            headers=auth_headers,
            json={
                "query": "test query",
                "top_k": 5,
                "minimum_score": 0.3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert isinstance(data["results"], list)

    @pytest.mark.asyncio
    async def test_search_with_kb_filter(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/retrieval/search",
            headers=auth_headers,
            json={
                "query": "test query",
                "top_k": 5,
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_hybrid_search(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/retrieval/hybrid-search",
            headers=auth_headers,
            json={
                "query": "hybrid search test",
                "top_k": 5,
                "alpha": 0.5,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    @pytest.mark.asyncio
    async def test_hybrid_search_with_rrf(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/retrieval/hybrid-search",
            headers=auth_headers,
            json={
                "query": "rrf test",
                "top_k": 5,
                "use_rrf": True,
                "rrf_k": 60,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data

    @pytest.mark.asyncio
    async def test_reranker(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/retrieval/rerank",
            headers=auth_headers,
            json={
                "query": "rerank test",
                "documents": [
                    {"id": "1", "text": "First document about testing"},
                    {"id": "2", "text": "Second document about something else"},
                    {"id": "3", "text": "Third document with test content"},
                ],
                "top_k": 2,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) <= 2

    @pytest.mark.asyncio
    async def test_query_expansion(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/retrieval/expand-query",
            headers=auth_headers,
            json={
                "query": "test query expansion",
                "max_expansions": 3,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "expanded_queries" in data
        assert isinstance(data["expanded_queries"], list)

    @pytest.mark.asyncio
    async def test_context_compression(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/retrieval/compress-context",
            headers=auth_headers,
            json={
                "query": "compress this context",
                "documents": [
                    {"id": "1", "text": "First document with relevant information about the query"},
                    {"id": "2", "text": "Second document with less relevant content"},
                    {"id": "3", "text": "Third document that is very long and contains lots of text " * 50},
                ],
                "max_tokens": 1000,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "compressed_context" in data
        assert "total_tokens" in data