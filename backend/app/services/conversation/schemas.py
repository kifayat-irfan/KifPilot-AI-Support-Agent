from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class ChatSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=255, description="Optional session title")


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    title: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_activity: datetime
    message_count: int


class ChatSessionListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sessions: List[ChatSessionResponse]
    total: int
    page: int
    page_size: int


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True)

    id: str
    session_id: str
    role: str
    message: str
    citations: Optional[List[Dict[str, Any]]] = None
    confidence: Optional[float] = None
    token_count: Optional[int] = None
    response_time_ms: Optional[float] = None
    created_at: datetime


class ChatConversationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: ChatSessionResponse
    messages: List[ChatMessageResponse]


class ChatSessionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Optional[str] = Field(None, max_length=255)


class SessionListParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    sort_by: str = Field(default="last_activity", pattern="^(created_at|updated_at|last_activity|message_count|title)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")


class MemoryConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    max_messages: int = Field(default=20, ge=1, le=100, description="Maximum messages to keep in context")
    max_tokens: int = Field(default=8000, ge=1000, le=32000, description="Maximum tokens for conversation context")
    include_system_prompt: bool = Field(default=True, description="Whether to include system prompt")


class StreamChatWithSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=2000, description="User's question")
    session_id: Optional[str] = Field(None, description="Existing session ID (creates new if not provided)")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    minimum_score: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filters")
    memory_config: Optional[MemoryConfig] = Field(None, description="Conversation memory configuration")