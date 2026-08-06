from abc import ABC, abstractmethod
from typing import List, Optional, AsyncGenerator
from uuid import UUID

from app.application.dto import (
    ConversationCreateDTO,
    ConversationUpdateDTO,
    ConversationResponseDTO,
    MessageCreateDTO,
    MessageResponseDTO,
    KnowledgeBaseCreateDTO,
    KnowledgeBaseUpdateDTO,
    KnowledgeBaseResponseDTO,
    DocumentCreateDTO,
    DocumentResponseDTO,
    DocumentChunkResponseDTO,
    ChatRequestDTO,
    ChatResponseDTO,
    SearchRequestDTO,
    SearchResponseDTO,
    SearchResultDTO,
    UserCreateDTO,
    UserResponseDTO,
    TokenDTO,
)


class ConversationUseCase(ABC):
    @abstractmethod
    async def create_conversation(self, dto: ConversationCreateDTO) -> ConversationResponseDTO:
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: UUID) -> Optional[ConversationResponseDTO]:
        pass

    @abstractmethod
    async def get_conversation_by_session(self, session_id: str) -> Optional[ConversationResponseDTO]:
        pass

    @abstractmethod
    async def update_conversation(
        self, conversation_id: UUID, dto: ConversationUpdateDTO
    ) -> Optional[ConversationResponseDTO]:
        pass

    @abstractmethod
    async def list_conversations(
        self, user_id: Optional[UUID] = None, offset: int = 0, limit: int = 100
    ) -> List[ConversationResponseDTO]:
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: UUID) -> bool:
        pass


class MessageUseCase(ABC):
    @abstractmethod
    async def add_message(self, dto: MessageCreateDTO) -> MessageResponseDTO:
        pass

    @abstractmethod
    async def get_messages(
        self, conversation_id: UUID, offset: int = 0, limit: int = 100
    ) -> List[MessageResponseDTO]:
        pass

    @abstractmethod
    async def get_last_messages(self, conversation_id: UUID, limit: int = 10) -> List[MessageResponseDTO]:
        pass


class KnowledgeBaseUseCase(ABC):
    @abstractmethod
    async def create_knowledge_base(self, dto: KnowledgeBaseCreateDTO) -> KnowledgeBaseResponseDTO:
        pass

    @abstractmethod
    async def get_knowledge_base(self, kb_id: UUID) -> Optional[KnowledgeBaseResponseDTO]:
        pass

    @abstractmethod
    async def update_knowledge_base(
        self, kb_id: UUID, dto: KnowledgeBaseUpdateDTO
    ) -> Optional[KnowledgeBaseResponseDTO]:
        pass

    @abstractmethod
    async def list_knowledge_bases(
        self, offset: int = 0, limit: int = 100
    ) -> List[KnowledgeBaseResponseDTO]:
        pass

    @abstractmethod
    async def delete_knowledge_base(self, kb_id: UUID) -> bool:
        pass


class DocumentUseCase(ABC):
    @abstractmethod
    async def upload_document(
        self, dto: DocumentCreateDTO, content: bytes
    ) -> DocumentResponseDTO:
        pass

    @abstractmethod
    async def get_document(self, doc_id: UUID) -> Optional[DocumentResponseDTO]:
        pass

    @abstractmethod
    async def list_documents(
        self, kb_id: UUID, offset: int = 0, limit: int = 100
    ) -> List[DocumentResponseDTO]:
        pass

    @abstractmethod
    async def delete_document(self, doc_id: UUID) -> bool:
        pass

    @abstractmethod
    async def process_document(self, doc_id: UUID) -> bool:
        pass


class ChatUseCase(ABC):
    @abstractmethod
    async def chat(self, dto: ChatRequestDTO) -> ChatResponseDTO:
        pass

    @abstractmethod
    async def chat_stream(self, dto: ChatRequestDTO) -> AsyncGenerator[str, None]:
        pass


class SearchUseCase(ABC):
    @abstractmethod
    async def search(self, dto: SearchRequestDTO) -> SearchResponseDTO:
        pass

    @abstractmethod
    async def similarity_search(
        self, query: str, kb_ids: List[UUID], limit: int, threshold: float
    ) -> List[SearchResultDTO]:
        pass


class AuthUseCase(ABC):
    @abstractmethod
    async def register(self, dto: UserCreateDTO) -> UserResponseDTO:
        pass

    @abstractmethod
    async def login(self, email: str, password: str) -> TokenDTO:
        pass

    @abstractmethod
    async def get_current_user(self, token: str) -> Optional[UserResponseDTO]:
        pass

    @abstractmethod
    async def refresh_token(self, token: str) -> TokenDTO:
        pass


class HealthUseCase(ABC):
    @abstractmethod
    async def check_health(self) -> dict:
        pass