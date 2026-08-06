from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from datetime import datetime


class Citation(BaseModel):
    """Citation for a factual statement in the answer."""
    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(..., description="Source document UUID")
    document_name: str = Field(..., description="Original document filename")
    page_number: Optional[int] = Field(None, description="Page number in document")
    section: Optional[str] = Field(None, description="Section heading")
    chunk_id: str = Field(..., description="Chunk UUID")
    chunk_index: int = Field(..., description="Chunk index within document")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")


class CitedAnswer(BaseModel):
    """Answer with inline citations."""
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(..., description="Generated answer text")
    citations: List[Citation] = Field(default_factory=list, description="All unique citations")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    sources_found: int = Field(..., description="Number of unique source documents")
    response_time_ms: float = Field(..., description="Total response time in milliseconds")


class CitationHealthResponse(BaseModel):
    """Health check response."""
    status: str
    citation_service_healthy: bool
    retrieval_service_healthy: bool
    error: Optional[str] = None