from abc import ABC, abstractmethod
from typing import List, Optional
from uuid import UUID

from app.domain.entities import Conversation, Message, KnowledgeBase, Document, DocumentChunk


class ConversationDomainService(ABC):
    @abstractmethod
    def generate_title(self, first_message: str) -> str:
        pass

    @abstractmethod
    def can_add_message(self, conversation: Conversation) -> bool:
        pass


class KnowledgeBaseDomainService(ABC):
    @abstractmethod
    def validate_document(self, filename: str, content_type: str, size_bytes: int) -> bool:
        pass

    @abstractmethod
    def calculate_chunks(self, content: str, chunk_size: int, chunk_overlap: int) -> List[str]:
        pass


class EmbeddingDomainService(ABC):
    @abstractmethod
    def generate_embedding(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        pass


class LLMDomainService(ABC):
    @abstractmethod
    async def generate_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        pass

    @abstractmethod
    async def generate_streaming_response(
        self,
        messages: List[Message],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        pass