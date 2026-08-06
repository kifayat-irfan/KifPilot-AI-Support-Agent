from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


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


class BaseEntity(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Conversation(BaseEntity):
    user_id: Optional[UUID] = None
    session_id: str
    status: ConversationStatus = ConversationStatus.ACTIVE
    title: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class Message(BaseEntity):
    conversation_id: UUID
    role: MessageRole
    content: str
    tokens_used: int = 0
    model_used: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class KnowledgeBase(BaseEntity):
    name: str
    description: Optional[str] = None
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE
    document_count: int = 0
    chunk_count: int = 0
    embedding_model: str = "nomic-embed-text"
    metadata: dict = Field(default_factory=dict)


class Document(BaseEntity):
    knowledge_base_id: UUID
    filename: str
    content_type: str
    size_bytes: int
    status: str = "pending"
    chunk_count: int = 0
    metadata: dict = Field(default_factory=dict)


class DocumentChunk(BaseEntity):
    document_id: UUID
    knowledge_base_id: UUID
    content: str
    chunk_index: int
    token_count: int
    embedding: Optional[List[float]] = None
    metadata: dict = Field(default_factory=dict)


class User(BaseEntity):
    email: str
    hashed_password: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_admin: bool = False
    last_login: Optional[datetime] = None