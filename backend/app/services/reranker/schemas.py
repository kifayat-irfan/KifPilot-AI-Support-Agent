"""Schemas for Cross-Encoder Re-ranker."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class RerankerConfig(BaseModel):
    """Configuration for the Cross-Encoder Re-ranker."""
    model_config = ConfigDict(extra="forbid")

    # Enable/disable reranking
    enabled: bool = Field(default=False, description="Enable Cross-Encoder re-ranking")
    
    # Model configuration
    model_name: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Cross-Encoder model name (HuggingFace Hub)"
    )
    model_cache_dir: Optional[str] = Field(
        default=None,
        description="Local directory to cache model"
    )
    
    # Performance settings
    max_candidates: int = Field(
        default=20,
        ge=5,
        le=100,
        description="Maximum candidates to rerank from hybrid search"
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum results to return after reranking"
    )
    timeout_seconds: float = Field(
        default=5.0,
        ge=0.5,
        le=30.0,
        description="Timeout for reranking in seconds"
    )
    
    # Batch processing
    batch_size: int = Field(
        default=16,
        ge=1,
        le=64,
        description="Batch size for cross-encoder inference"
    )
    
    # Score thresholds
    min_rerank_score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum reranker score to keep result"
    )


class RerankerCandidate(BaseModel):
    """A candidate from hybrid search to be reranked."""
    model_config = ConfigDict(extra="allow")

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document ID")
    document_name: str = Field(..., description="Document filename")
    chunk_index: int = Field(..., description="Chunk index within document")
    page: Optional[int] = Field(None, description="Page number")
    section: Optional[str] = Field(None, description="Section heading")
    text: str = Field(..., description="Chunk text content")
    hybrid_score: float = Field(..., ge=0.0, le=1.0, description="Hybrid search score (RRF)")
    vector_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Vector similarity score")
    bm25_score: Optional[float] = Field(None, ge=0.0, description="BM25 score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RerankedResult(BaseModel):
    """A reranked result with all scores."""
    model_config = ConfigDict(extra="allow")

    chunk_id: str = Field(..., description="Unique chunk identifier")
    document_id: str = Field(..., description="Parent document ID")
    document_name: str = Field(..., description="Document filename")
    chunk_index: int = Field(..., description="Chunk index within document")
    page: Optional[int] = Field(None, description="Page number")
    section: Optional[str] = Field(None, description="Section heading")
    text: str = Field(..., description="Chunk text content")
    
    # Scores
    hybrid_score: float = Field(..., ge=0.0, le=1.0, description="Hybrid search score (RRF)")
    reranker_score: float = Field(..., ge=0.0, le=1.0, description="Cross-Encoder reranker score")
    final_score: float = Field(..., ge=0.0, le=1.0, description="Final combined score")
    
    # Optional component scores
    vector_score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Vector similarity score")
    bm25_score: Optional[float] = Field(None, ge=0.0, description="BM25 score")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class RerankerRequest(BaseModel):
    """Request for reranking."""
    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1, max_length=2000, description="Original search query")
    candidates: List[RerankerCandidate] = Field(
        ..., 
        min_length=1, 
        max_length=100,
        description="Candidates from hybrid search to rerank"
    )
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results to return")


class RerankerResponse(BaseModel):
    """Response from reranker."""
    model_config = ConfigDict(extra="forbid")

    results: List[RerankedResult] = Field(..., description="Reranked results")
    reranker_time_ms: float = Field(..., description="Reranking execution time in milliseconds")
    total_candidates: int = Field(..., description="Total candidates received")
    returned_count: int = Field(..., description="Number of results returned")
    fallback: bool = Field(default=False, description="Whether fallback to hybrid scores was used")


class RerankerHealthResponse(BaseModel):
    """Health check response for reranker."""
    status: Literal["healthy", "unhealthy", "degraded", "unavailable"]
    model_loaded: bool = False
    model_name: Optional[str] = None
    model_device: Optional[str] = None
    fallback_mode: bool = False
    error: Optional[str] = None