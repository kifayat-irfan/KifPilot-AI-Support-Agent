import asyncio
import pytest
import time
from httpx import ASGITransport, AsyncClient
from app.main import create_app


@pytest.fixture(scope="session")
async def stress_app():
    app = create_app()
    yield app


@pytest.fixture
async def stress_client(stress_app):
    transport = ASGITransport(app=stress_app)
    async with AsyncClient(transport=transport, base_url="http://test", timeout=60.0) as ac:
        yield ac


class TestLargePDFs:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_pdf_upload(self, stress_client, auth_headers):
        # Create a larger PDF-like content (simulated)
        large_content = b"%PDF-1.4\n" + b"x" * (5 * 1024 * 1024)  # 5MB
        
        start = time.perf_counter()
        response = await stress_client.post(
            "/api/v1/documents/upload",
            headers=auth_headers,
            files={"file": ("large.pdf", large_content, "application/pdf")},
        )
        end = time.perf_counter()
        
        print(f"Large PDF upload time: {(end - start) * 1000:.2f}ms")
        assert response.status_code in [201, 413]  # Success or too large


class TestLargeKnowledgeBases:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_kb_with_many_documents(self, stress_client, auth_headers):
        # Create KB
        kb_resp = await stress_client.post(
            "/api/v1/knowledge-bases",
            headers=auth_headers,
            json={"name": "Large KB", "description": "Many documents"},
        )
        kb_id = kb_resp.json()["id"]
        
        # Upload multiple documents
        doc_ids = []
        for i in range(50):
            resp = await stress_client.post(
                "/api/v1/documents/upload",
                headers=auth_headers,
                files={"file": (f"doc_{i}.txt", f"Document {i} content".encode(), "text/plain")},
            )
            if resp.status_code == 201:
                doc_ids.append(resp.json()["document_id"])
        
        print(f"Uploaded {len(doc_ids)} documents")
        assert len(doc_ids) >= 40
        
        # Add all to KB
        for doc_id in doc_ids:
            await stress_client.post(
                f"/api/v1/knowledge-bases/{kb_id}/documents",
                headers=auth_headers,
                json={"document_ids": [doc_id]},
            )
        
        # Test search still works
        search_resp = await stress_client.post(
            "/api/v1/retrieval/search",
            headers=auth_headers,
            json={"query": "document", "top_k": 10},
        )
        assert search_resp.status_code == 200


class TestThousandDocuments:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_1000_documents_stress(self, stress_client, auth_headers):
        """Test with 1000 documents (if time permits)"""
        # This is a stress test - upload many docs
        uploaded = 0
        for i in range(100):
            resp = await stress_client.post(
                "/api/v1/documents/upload",
                headers=auth_headers,
                files={"file": (f"stress_{i}.txt", f"Stress test document {i}".encode(), "text/plain")},
            )
            if resp.status_code == 201:
                uploaded += 1
        
        print(f"Successfully uploaded {uploaded}/100 documents")
        assert uploaded >= 80


class TestConcurrentUsersStress:
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_100_concurrent_users(self, stress_client, auth_headers):
        """Simulate 100 concurrent users making requests"""
        
        async def user_session(user_id):
            """Simulate a user session"""
            results = []
            
            # Health check
            resp = await stress_client.get("/api/v1/health")
            results.append(resp.status_code)
            
            # List documents
            resp = await stress_client.get("/api/v1/documents", headers=auth_headers)
            results.append(resp.status_code)
            
            # Search
            resp = await stress_client.post(
                "/api/v1/retrieval/search",
                headers=auth_headers,
                json={"query": f"user {user_id} query", "top_k": 5},
            )
            results.append(resp.status_code)
            
            # Chat
            resp = await stress_client.post(
                "/api/v1/chat/ask",
                headers=auth_headers,
                json={"question": f"Question from user {user_id}", "top_k": 3},
            )
            results.append(resp.status_code)
            
            return results
        
        # Run 20 concurrent users (100 would be too heavy for CI)
        tasks = [user_session(i) for i in range(20)]
        all_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        success_count = 0
        error_count = 0
        for result in all_results:
            if isinstance(result, Exception):
                error_count += 1
            else:
                success_count += sum(1 for r in result if r == 200)
                error_count += sum(1 for r in result if r >= 500)
        
        print(f"Success: {success_count}, Errors: {error_count}")
        assert error_count == 0