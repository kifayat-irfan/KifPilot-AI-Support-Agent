from typing import List, Optional, AsyncGenerator
from app.infrastructure.llm.client import ollama_client
from app.infrastructure.llm.repository import LLMRepository
from app.domain.entities import Message, MessageRole
from app.core.config import get_settings
from app.core.exceptions import LLMException
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class OllamaLLMRepository(LLMRepository):
    def __init__(self):
        self._client = ollama_client

    def _messages_to_ollama_format(
        self, messages: List[Message], system_prompt: Optional[str] = None
    ) -> List[dict]:
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({"role": "system", "content": system_prompt})
        for msg in messages:
            ollama_messages.append({"role": msg.role.value, "content": msg.content})
        return ollama_messages

    async def generate_completion(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        try:
            ollama_messages = self._messages_to_ollama_format(messages, system_prompt)
            response = await self._client.chat(
                messages=ollama_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=False,
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error("LLM completion failed", error=str(e))
            raise LLMException(f"Completion failed: {str(e)}")

    async def generate_streaming_completion(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        try:
            ollama_messages = self._messages_to_ollama_format(messages, system_prompt)
            stream = await self._client.chat(
                messages=ollama_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]
        except Exception as e:
            logger.error("LLM streaming failed", error=str(e))
            raise LLMException(f"Streaming failed: {str(e)}")

    async def generate_embedding(self, text: str) -> List[float]:
        try:
            embeddings = await self._client.embed(input=[text])
            return embeddings[0] if embeddings else []
        except Exception as e:
            logger.error("Embedding generation failed", error=str(e))
            raise LLMException(f"Embedding failed: {str(e)}")

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            return await self._client.embed(input=texts)
        except Exception as e:
            logger.error("Batch embedding generation failed", error=str(e))
            raise LLMException(f"Batch embedding failed: {str(e)}")

    async def health_check(self) -> bool:
        return await self._client.health_check()