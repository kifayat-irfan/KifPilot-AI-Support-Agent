import ollama
from typing import List, Optional, AsyncGenerator
from app.core.config import get_settings
from app.core.exceptions import LLMException
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class OllamaClient:
    def __init__(self):
        self._client: ollama.AsyncClient | None = None
        self._sync_client: ollama.Client | None = None

    @property
    def client(self) -> ollama.AsyncClient:
        if self._client is None:
            self._client = ollama.AsyncClient(host=settings.OLLAMA_BASE_URL)
        return self._client

    @property
    def sync_client(self) -> ollama.Client:
        if self._sync_client is None:
            self._sync_client = ollama.Client(host=settings.OLLAMA_BASE_URL)
        return self._sync_client

    async def chat(
        self,
        messages: List[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        stream: bool = False,
    ) -> dict | AsyncGenerator:
        try:
            return await self.client.chat(
                model=model or settings.OLLAMA_CHAT_MODEL,
                messages=messages,
                options={
                    "temperature": temperature,
                    "num_predict": max_tokens,
                },
                stream=stream,
            )
        except Exception as e:
            logger.error("Ollama chat failed", error=str(e))
            raise LLMException(f"Chat failed: {str(e)}")

    async def embed(
        self,
        input: str | List[str],
        model: str | None = None,
    ) -> List[List[float]]:
        try:
            response = await self.client.embed(
                model=model or settings.OLLAMA_EMBEDDING_MODEL,
                input=input,
            )
            return response.embeddings
        except Exception as e:
            logger.error("Ollama embed failed", error=str(e))
            raise LLMException(f"Embedding failed: {str(e)}")

    async def list_models(self) -> List[str]:
        try:
            response = await self.client.list()
            return [model.model for model in response.models]
        except Exception as e:
            logger.error("Failed to list models", error=str(e))
            raise LLMException(f"Failed to list models: {str(e)}")

    async def pull_model(self, model: str) -> bool:
        try:
            await self.client.pull(model)
            return True
        except Exception as e:
            logger.error("Failed to pull model", model=model, error=str(e))
            raise LLMException(f"Failed to pull model: {str(e)}")

    async def check_model_exists(self, model: str) -> bool:
        try:
            models = await self.list_models()
            return model in models
        except Exception:
            return False

    async def health_check(self) -> bool:
        try:
            await self.client.ps()
            return True
        except Exception:
            return False


ollama_client = OllamaClient()