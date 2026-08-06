from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID


class RAGAskRequest(BaseModel):
    """Request for RAG answer generation."""
    model_config = ConfigDict(extra="forbid")

    question: str = Field(..., min_length=1, max_length=2000, description="User question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of chunks to retrieve")
    minimum_score: float = Field(default=0.65, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    filters: Optional[Dict[str, Any]] = Field(None, description="Optional metadata filters")

    @validator("question")
    def validate_question(cls, v):
        if not v or not v.strip():
            raise ValueError("Question cannot be empty")
        # Check for prompt injection attempts
        injection_patterns = [
            "ignore previous instructions",
            "ignore the above",
            "forget everything",
            "system prompt",
            "you are now",
            "act as",
            "pretend to be",
            "disregard",
            "override",
        ]
        lower = v.lower()
        for pattern in injection_patterns:
            if pattern in lower:
                raise ValueError("Question contains potential prompt injection")
        # Check for extremely long questions
        if len(v) > 2000:
            raise ValueError("Question too long")
        return v.strip()


class RAGSource(BaseModel):
    """Source document reference."""
    model_config = ConfigDict(extra="forbid")

    document_id: str
    document_name: str
    chunk_id: str
    chunk_index: int
    page: Optional[int] = None
    section: Optional[str] = None
    similarity_score: float


class RAGAskResponse(BaseModel):
    """Response for RAG answer generation."""
    model_config = ConfigDict(extra="forbid")

    answer: str
    sources_found: int
    response_time_ms: float
    confidence: float
    sources: Optional[List[RAGSource]] = None


class RAGHealthResponse(BaseModel):
    """Health check response."""
    status: str
    retrieval_service_healthy: bool
    ollama_service_healthy: bool
    error: Optional[str] = None