from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from app.services.citations.schemas import Citation


class StreamChatRequest(BaseModel):
    """Request for streaming chat."""
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=2000, description="User's question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    minimum_score: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filters")


class StreamStartEvent(BaseModel):
    """Event emitted when streaming starts."""
    event: str = "start"
    status: str = "started"


class StreamRetrievalEvent(BaseModel):
    """Event emitted after retrieval completes."""
    event: str = "retrieval"
    chunks_found: int
    search_time_ms: float


class StreamTokenEvent(BaseModel):
    """Event emitted for each token chunk."""
    event: str = "token"
    text: str


class StreamCitationsEvent(BaseModel):
    """Event emitted with citations after generation."""
    event: str = "citations"
    citations: List[Citation]


class StreamCompleteEvent(BaseModel):
    """Event emitted when streaming completes."""
    event: str = "complete"
    confidence: float
    sources_found: int
    response_time_ms: float


class StreamErrorEvent(BaseModel):
    """Event emitted on error."""
    event: str = "error"
    error: str
    code: str


class StreamHealthResponse(BaseModel):
    """Health check response."""
    status: str
    streaming_service_healthy: bool
    retrieval_service_healthy: bool
    rag_service_healthy: bool
    ollama_service_healthy: bool
    error: Optional[str] = None


class StreamChatResponse(BaseModel):
    """Complete non-streaming response for backward compatibility."""
    answer: str
    citations: List[Citation]
    confidence: float
    sources_found: int
    response_time_ms: float


# Union type for all possible stream events
StreamEvent = (
    StreamStartEvent 
    | StreamRetrievalEvent 
    | StreamTokenEvent 
    | StreamCitationsEvent 
    | StreamCompleteEvent 
    | StreamErrorEvent
)