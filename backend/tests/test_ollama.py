import pytest
from httpx import ASGITransport, AsyncClient
from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_ollama_health(client: AsyncClient):
    response = await client.get("/api/v1/ollama/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "ollama_running" in data
    assert "chat_model_available" in data
    assert "embed_model_available" in data
    assert data["base_url"] == "http://localhost:11434"
    assert data["chat_model"] == "qwen3.5:4b"
    assert data["embed_model"] == "nomic-embed-text"


@pytest.mark.asyncio
async def test_list_models(client: AsyncClient):
    response = await client.get("/api/v1/ollama/models")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert isinstance(data["models"], list)


@pytest.mark.asyncio
async def test_chat_empty_prompt(client: AsyncClient):
    response = await client.post(
        "/api/v1/ollama/chat",
        json={"messages": []},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_chat_stream_empty_prompt(client: AsyncClient):
    response = await client.post(
        "/api/v1/ollama/chat/stream",
        json={"messages": []},
    )
    assert response.status_code == 422