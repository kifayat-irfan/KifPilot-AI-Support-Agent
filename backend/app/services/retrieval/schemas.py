from pydantic import BaseModel, Field, ConfigDict, validator
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from uuid import UUID


class RetrievalFilters(BaseModel):
    """Filters for retrieval search."""
    model_config = ConfigDict(extra="forbid")

    company: Optional[str] = Field(None, description="Filter by company")
    category: Optional[str] = Field(None, description="Filter by document category")
    language: Optional[str] = Field(None, description="Filter by document language (ISO 639-1)")
    document_id: Optional[str] = Field(None, description="Filter by specific document ID")
    file_type: Optional[str] = Field(None, description="Filter by file type")
    processing_status: Optional[str] = Field(None, description="Filter by processing status")
    created_after: Optional[datetime] = Field(None, description="Filter documents created after this date")
    created_before: Optional[datetime] = Field(None, description="Filter documents created before this date")

    @validator("document_id")
    def validate_document_id(cls, v):
        if v is not None:
            try:
                UUID(v)
            except ValueError:
                raise ValueError("Invalid document_id UUID format")
        return v


class RetrievalSearchRequest(BaseModel):
    """Request for semantic search."""
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000, description="Search query text")
    top_k: int = Field(default=10, ge=1, le=20, description="Number of results to return")
    minimum_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    filters: Optional[RetrievalFilters] = Field(None, description="Metadata filters")


class RetrievalResult(BaseModel):
    """Individual retrieval result."""
    model_config = ConfigDict(extra="allow")

    document_id: str = Field(..., description="Source document UUID")
    document_name: str = Field(..., description="Original document filename")
    chunk_id: str = Field(..., description="Chunk UUID")
    chunk_index: int = Field(..., description="Chunk index within document")
    page: Optional[int] = Field(None, description="Page number")
    section: Optional[str] = Field(None, description="Section heading")
    text: str = Field(..., description="Chunk text content")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Normalized similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RetrievalSearchResponse(BaseModel):
    """Response for semantic search."""
    model_config = ConfigDict(extra="forbid")

    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    total_results: int = Field(..., description="Total number of results found")
    results: List[RetrievalResult] = Field(..., description="Retrieved chunks")


class RetrievalContextRequest(BaseModel):
    """Request for building context from search results."""
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000, description="Original search query")
    top_k: int = Field(default=10, ge=1, le=20, description="Number of chunks to include")
    minimum_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    filters: Optional[RetrievalFilters] = Field(None, description="Metadata filters")
    max_context_chars: int = Field(default=8000, ge=500, le=32000, description="Maximum context size in characters")


class RetrievalContextResponse(BaseModel):
    """Response with built context for RAG."""
    model_config = ConfigDict(extra="forbid")

    context: str = Field(..., description="Built context string")
    search_time_ms: float = Field(..., description="Search execution time in milliseconds")
    total_chunks: int = Field(..., description="Number of chunks used in context")
    total_chars: int = Field(..., description="Total characters in context")
    sources: List[RetrievalResult] = Field(..., description="Source chunks used")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: Literal["healthy", "unhealthy"]
    vector_store_connected: bool
    embedding_service_available: bool
    error: Optional[str] = None