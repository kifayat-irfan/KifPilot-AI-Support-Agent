from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator
from app.domain.entities import Message, MessageRole


class LLMRepository(ABC):
    @abstractmethod
    async def generate_completion(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        pass

    @abstractmethod
    async def generate_streaming_completion(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass