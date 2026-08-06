from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from uuid import UUID

from app.domain.entities import (
    Conversation,
    Message,
    KnowledgeBase,
    Document,
    DocumentChunk,
    User,
)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    @abstractmethod
    async def create(self, entity: T) -> T:
        pass

    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[T]:
        pass

    @abstractmethod
    async def update(self, entity: T) -> T:
        pass

    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        pass

    @abstractmethod
    async def list(self, offset: int = 0, limit: int = 100) -> List[T]:
        pass


class ConversationRepository(BaseRepository[Conversation]):
    @abstractmethod
    async def get_by_session_id(self, session_id: str) -> Optional[Conversation]:
        pass

    @abstractmethod
    async def get_by_user_id(self, user_id: UUID, offset: int = 0, limit: int = 100) -> List[Conversation]:
        pass

    @abstractmethod
    async def update_status(self, id: UUID, status: str) -> bool:
        pass


class MessageRepository(BaseRepository[Message]):
    @abstractmethod
    async def get_by_conversation_id(
        self, conversation_id: UUID, offset: int = 0, limit: int = 100
    ) -> List[Message]:
        pass

    @abstractmethod
    async def get_last_messages(self, conversation_id: UUID, limit: int = 10) -> List[Message]:
        pass


class KnowledgeBaseRepository(BaseRepository[KnowledgeBase]):
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[KnowledgeBase]:
        pass

    @abstractmethod
    async def update_status(self, id: UUID, status: str) -> bool:
        pass

    @abstractmethod
    async def increment_counts(self, id: UUID, doc_count: int = 0, chunk_count: int = 0) -> bool:
        pass


class DocumentRepository(BaseRepository[Document]):
    @abstractmethod
    async def get_by_knowledge_base_id(
        self, knowledge_base_id: UUID, offset: int = 0, limit: int = 100
    ) -> List[Document]:
        pass

    @abstractmethod
    async def update_status(self, id: UUID, status: str) -> bool:
        pass


class DocumentChunkRepository(BaseRepository[DocumentChunk]):
    @abstractmethod
    async def get_by_document_id(self, document_id: UUID) -> List[DocumentChunk]:
        pass

    @abstractmethod
    async def get_by_knowledge_base_id(self, knowledge_base_id: UUID) -> List[DocumentChunk]:
        pass

    @abstractmethod
    async def bulk_create(self, chunks: List[DocumentChunk]) -> List[DocumentChunk]:
        pass


class UserRepository(BaseRepository[User]):
    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def update_last_login(self, id: UUID) -> bool:
        pass