import asyncio
import pytest
import time
from httpx import ASGITransport, AsyncClient
from app.main import create_app


@pytest.fixture(scope="session")
async def load_app():
    app = create_app()
    yield app


@pytest.fixture
async def load_client(load_app):
    transport = ASGITransport(app=load_app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=30.0) as ac:
        yield ac


class TestConcurrentUsers:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_health_checks(self, load_client):
        async def make_request():
            response = await load_client.get("/api/v1/health")
            return response.status_code
        
        # 50 concurrent requests
        tasks = [make_request() for _ in range(50)]
        results = await asyncio.gather(*tasks)
        
        # All should succeed (or rate limited)
        success_count = sum(1 for r in results if r == 200)
        rate_limited = sum(1 for r in results if r == 429)
        assert success_count + rate_limited == 50

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_auth_requests(self, load_client):
        async def login_attempt():
            response = await load_client.post(
                "/api/v1/auth/login",
                json={"email": "loadtest@example.com", "password": "password123"},
            )
            return response.status_code
        
        # 20 concurrent login attempts
        tasks = [login_attempt() for _ in range(20)]
        results = await asyncio.gather(*tasks)
        
        # Should handle gracefully
        assert all(r in [200, 401, 429] for r in results)


class TestConcurrentChats:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_chat_requests(self, load_client, auth_headers):
        async def chat_request():
            response = await load_client.post(
                "/api/v1/chat/ask",
                headers=auth_headers,
                json={"question": "Concurrent chat test", "top_k": 3},
            )
            return response.status_code
        
        # 10 concurrent chats
        tasks = [chat_request() for _ in range(10)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Check results
        success = sum(1 for r in results if r == 200)
        errors = sum(1 for r in results if isinstance(r, Exception) or (isinstance(r, int) and r >= 500))
        assert errors == 0


class TestConcurrentUploads:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_document_uploads(self, load_client, auth_headers):
        async def upload_document(index):
            response = await load_client.post(
                "/api/v1/documents/upload",
                headers=auth_headers,
                files={"file": (f"concurrent_{index}.txt", f"Content {index}".encode(), "text/plain")},
            )
            return response.status_code
        
        # 5 concurrent uploads
        tasks = [upload_document(i) for i in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success = sum(1 for r in results if r == 201 or r == 200)
        assert success >= 3  # At least 3 should succeed


class TestStreamingLoad:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_streaming(self, load_client, auth_headers):
        async def stream_request():
            response = await load_client.post(
                "/api/v1/chat/stream",
                headers=auth_headers,
                json={"question": "Stream load test", "top_k": 3},
            )
            return response.status_code
        
        # 5 concurrent streams
        tasks = [stream_request() for _ in range(5)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success = sum(1 for r in results if r == 200)
        assert success >= 3


class TestRetrievalLoad:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_retrieval_search(self, load_client, auth_headers):
        async def search_request():
            response = await load_client.post(
                "/api/v1/retrieval/search",
                headers=auth_headers,
                json={"query": "load test query", "top_k": 5},
            )
            return response.status_code
        
        # 20 concurrent searches
        tasks = [search_request() for _ in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success = sum(1 for r in results if r == 200)
        assert success >= 15


class TestPerformance:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_health_endpoint_latency(self, load_client):
        latencies = []
        for _ in range(100):
            start = time.perf_counter()
            response = await load_client.get("/api/v1/health")
            end = time.perf_counter()
            if response.status_code == 200:
                latencies.append((end - start) * 1000)  # ms
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            p95_latency = sorted(latencies)[int(len(latencies) * 0.95)]
            print(f"Avg latency: {avg_latency:.2f}ms, P95: {p95_latency:.2f}ms")
            assert avg_latency < 100  # Average under 100ms
            assert p95_latency < 500  # P95 under 500ms

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_chat_response_time(self, load_client, auth_headers):
        latencies = []
        for _ in range(10):
            start = time.perf_counter()
            response = await load_client.post(
                "/api/v1/chat/ask",
                headers=auth_headers,
                json={"question": "Performance test", "top_k": 3},
            )
            end = time.perf_counter()
            if response.status_code == 200:
                latencies.append((end - start) * 1000)
        
        if latencies:
            avg_latency = sum(latencies) / len(latencies)
            print(f"Chat avg latency: {avg_latency:.2f}ms")
            assert avg_latency < 5000  # Under 5 seconds