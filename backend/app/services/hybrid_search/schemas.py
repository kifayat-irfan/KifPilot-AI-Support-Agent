from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from uuid import UUID


class HybridSearchRequest(BaseModel):
    """Request for hybrid search combining vector and BM25 search."""
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000, description="Search query text")
    top_k: int = Field(default=10, ge=1, le=20, description="Number of results to return")
    minimum_score: float = Field(default=0.0, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    rrf_constant: int = Field(default=60, ge=1, le=1000, description="RRF constant for rank fusion (k in RRF formula)")
    vector_weight: float = Field(default=1.0, ge=0.0, le=2.0, description="Weight for vector search results in fusion")
    bm25_weight: float = Field(default=1.0, ge=0.0, le=2.0, description="Weight for BM25 search results in fusion")
    filters: Optional["HybridSearchFilters"] = Field(None, description="Metadata filters")
    include_vector_scores: bool = Field(default=True, description="Include individual vector scores in response")
    include_bm25_scores: bool = Field(default=True, description="Include individual BM25 scores in response")


class HybridSearchFilters(BaseModel):
    """Filters for hybrid search."""
    model_config = ConfigDict(extra="forbid")

    company: Optional[str] = Field(None, description="Filter by company")
    category: Optional[str] = Field(None, description="Filter by document category")
    language: Optional[str] = Field(None, description="Filter by document language (ISO 639-1)")
    document_id: Optional[str] = Field(None, description="Filter by specific document ID")
    file_type: Optional[str] = Field(None, description="Filter by file type")
    processing_status: Optional[str] = Field(None, description="Filter by processing status")
    created_after: Optional[datetime] = Field(None, description="Filter documents created after this date")
    created_before: Optional[datetime] = Field(None, description="Filter documents created before this date")

    @classmethod
    def from_retrieval_filters(cls, filters: "RetrievalFilters") -> "HybridSearchFilters":
        """Create HybridSearchFilters from existing RetrievalFilters."""
        if not filters:
            return None
        return cls(
            company=filters.company,
            category=filters.category,
            language=filters.language,
            document_id=filters.document_id,
            file_type=filters.file_type,
            processing_status=filters.processing_status,
            created_after=filters.created_after,
            created_before=filters.created_before,
        )


class HybridSearchResult(BaseModel):
    """Individual hybrid search result with RRF and component scores."""
    model_config = ConfigDict(extra="allow")

    document_id: str = Field(..., description="Source document UUID")
    document_name: str = Field(..., description="Original document filename")
    chunk_id: str = Field(..., description="Chunk UUID")
    chunk_index: int = Field(..., description="Chunk index within document")
    page: Optional[int] = Field(None, description="Page number")
    section: Optional[str] = Field(None, description="Section heading")
    text: str = Field(..., description="Chunk text content")
    rrf_score: float = Field(..., ge=0.0, le=1.0, description="RRF fused score")
    vector_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Vector similarity score")
    bm25_score: Optional[float] = Field(None, ge=0.0, description="BM25 score (raw)")
    normalized_bm25_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Normalized BM25 score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class HybridSearchResponse(BaseModel):
    """Response for hybrid search."""
    model_config = ConfigDict(extra="forbid")

    search_time_ms: float = Field(..., description="Total search execution time in milliseconds")
    vector_search_time_ms: float = Field(..., description="Vector search execution time in milliseconds")
    bm25_search_time_ms: float = Field(..., description="BM25 search execution time in milliseconds")
    fusion_time_ms: float = Field(..., description="Rank fusion execution time in milliseconds")
    total_results: int = Field(..., description="Total number of results found")
    results: List[HybridSearchResult] = Field(..., description="Retrieved chunks with fused scores")


class HybridSearchHealthResponse(BaseModel):
    """Health check response for hybrid search."""
    status: Literal["healthy", "unhealthy", "degraded"]
    vector_store_connected: bool
    embedding_service_available: bool
    bm25_index_loaded: bool
    bm25_index_chunk_count: int
    bm25_last_updated: Optional[datetime] = None
    error: Optional[str] = None


# Import RetrievalFilters for forward reference
from app.services.retrieval.schemas import RetrievalFilters