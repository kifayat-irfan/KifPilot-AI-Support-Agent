"""
Retrieval Engine - Semantic search and context building for RAG.

This module provides a production-grade retrieval engine that:
- Performs semantic vector search using ChromaDB
- Applies metadata filters (company, category, language, etc.)
- Ranks results using similarity, quality, and freshness signals
- Builds clean context for RAG with deduplication and size limits
"""

from app.services.retrieval.service import RetrievalService, retrieval_service
from app.services.retrieval.search import RetrievalSearcher
from app.services.retrieval.ranking import RetrievalRanker
from app.services.retrieval.context_builder import ContextBuilder
from app.services.retrieval.filters import FilterBuilder
from app.services.retrieval.schemas import (
    RetrievalFilters,
    RetrievalSearchRequest,
    RetrievalSearchResponse,
    RetrievalResult,
    RetrievalContextRequest,
    RetrievalContextResponse,
    HealthCheckResponse,
)
from app.services.retrieval.exceptions import (
    RetrievalError,
    EmptyQueryError,
    InvalidFiltersError,
    InvalidTopKError,
    InvalidUUIDError,
    EmbeddingGenerationError,
    VectorSearchError,
    ContextBuildError,
    NoResultsError,
)

__all__ = [
    # Services
    "RetrievalService",
    "retrieval_service",
    "RetrievalSearcher",
    "RetrievalRanker",
    "ContextBuilder",
    "FilterBuilder",
    # Schemas
    "RetrievalFilters",
    "RetrievalSearchRequest",
    "RetrievalSearchResponse",
    "RetrievalResult",
    "RetrievalContextRequest",
    "RetrievalContextResponse",
    "HealthCheckResponse",
    # Exceptions
    "RetrievalError",
    "EmptyQueryError",
    "InvalidFiltersError",
    "InvalidTopKError",
    "InvalidUUIDError",
    "EmbeddingGenerationError",
    "VectorSearchError",
    "ContextBuildError",
    "NoResultsError",
]