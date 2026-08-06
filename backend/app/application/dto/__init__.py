from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    ESCALATED = "escalated"


class KnowledgeBaseStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROCESSING = "processing"


class BaseDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ConversationCreateDTO(BaseDTO):
    session_id: str
    user_id: Optional[UUID] = None
    title: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class ConversationUpdateDTO(BaseDTO):
    title: Optional[str] = None
    status: Optional[ConversationStatus] = None
    metadata: Optional[dict] = None


class ConversationResponseDTO(BaseDTO):
    id: UUID
    user_id: Optional[UUID]
    session_id: str
    status: ConversationStatus
    title: Optional[str]
    metadata: dict
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


class MessageCreateDTO(BaseDTO):
    conversation_id: UUID
    role: MessageRole
    content: str
    metadata: dict = Field(default_factory=dict)


class MessageResponseDTO(BaseDTO):
    id: UUID
    conversation_id: UUID
    role: MessageRole
    content: str
    tokens_used: int
    model_used: Optional[str]
    metadata: dict
    created_at: datetime


class KnowledgeBaseCreateDTO(BaseDTO):
    name: str
    description: Optional[str] = None
    embedding_model: str = "nomic-embed-text"
    metadata: dict = Field(default_factory=dict)


class KnowledgeBaseUpdateDTO(BaseDTO):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[KnowledgeBaseStatus] = None
    metadata: Optional[dict] = None


class KnowledgeBaseResponseDTO(BaseDTO):
    id: UUID
    name: str
    description: Optional[str]
    status: KnowledgeBaseStatus
    document_count: int
    chunk_count: int
    embedding_model: str
    metadata: dict
    created_at: datetime
    updated_at: datetime


class DocumentCreateDTO(BaseDTO):
    knowledge_base_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    metadata: dict = Field(default_factory=dict)


class DocumentResponseDTO(BaseDTO):
    id: UUID
    knowledge_base_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str
    chunk_count: int
    metadata: dict
    created_at: datetime
    updated_at: datetime


class DocumentChunkResponseDTO(BaseDTO):
    id: UUID
    document_id: UUID
    knowledge_base_id: UUID
    content: str
    chunk_index: int
    token_count: int
    metadata: dict
    created_at: datetime


class ChatRequestDTO(BaseDTO):
    message: str
    conversation_id: Optional[UUID] = None
    session_id: Optional[str] = None
    knowledge_base_ids: List[UUID] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 2048
    stream: bool = False


class ChatResponseDTO(BaseDTO):
    conversation_id: UUID
    message: MessageResponseDTO
    sources: List[DocumentChunkResponseDTO] = Field(default_factory=list)


class SearchRequestDTO(BaseDTO):
    query: str
    knowledge_base_ids: List[UUID] = Field(default_factory=list)
    limit: int = 5
    threshold: float = 0.7


class SearchResultDTO(BaseDTO):
    chunk: DocumentChunkResponseDTO
    score: float


class SearchResponseDTO(BaseDTO):
    results: List[SearchResultDTO]
    query: str


class TokenDTO(BaseDTO):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserCreateDTO(BaseDTO):
    email: str
    password: str
    full_name: Optional[str] = None


class UserResponseDTO(BaseDTO):
    id: UUID
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]


class HealthCheckDTO(BaseDTO):
    status: str
    version: str
    environment: str
    database: str
    vector_store: str
    llm: str