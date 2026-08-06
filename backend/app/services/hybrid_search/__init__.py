"""Hybrid Search Service - Combines vector and BM25 search with RRF fusion."""

from app.services.hybrid_search.schemas import (
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchResult,
    HybridSearchFilters,
    HybridSearchHealthResponse,
)

from app.services.hybrid_search.exceptions import (
    HybridSearchError,
    EmptyQueryError,
    InvalidTopKError,
    InvalidRRFConstantError,
    InvalidWeightError,
    BM25IndexError,
    BM25IndexNotFoundError,
    BM25IndexBuildError,
    BM25IndexUpdateError,
    BM25SearchError,
    FusionError,
    VectorSearchError,
    EmbeddingGenerationError,
    InvalidFiltersError,
)

from app.services.hybrid_search.bm25 import BM25Indexer, BM25Document, BM25IndexState, bm25_indexer

from app.services.hybrid_search.fusion import (
    reciprocal_rank_fusion,
    weighted_score_fusion,
    deduplicate_results,
    normalize_scores,
)

from app.services.hybrid_search.hybrid import HybridSearchService, hybrid_search_service

__all__ = [
    # Schemas
    "HybridSearchRequest",
    "HybridSearchResponse",
    "HybridSearchResult",
    "HybridSearchFilters",
    "HybridSearchHealthResponse",
    # Exceptions
    "HybridSearchError",
    "EmptyQueryError",
    "InvalidTopKError",
    "InvalidRRFConstantError",
    "InvalidWeightError",
    "BM25IndexError",
    "BM25IndexNotFoundError",
    "BM25IndexBuildError",
    "BM25IndexUpdateError",
    "BM25SearchError",
    "FusionError",
    "VectorSearchError",
    "EmbeddingGenerationError",
    "InvalidFiltersError",
    # BM25
    "BM25Indexer",
    "BM25Document",
    "BM25IndexState",
    "bm25_indexer",
    # Fusion
    "reciprocal_rank_fusion",
    "weighted_score_fusion",
    "deduplicate_results",
    "normalize_scores",
    # Service
    "HybridSearchService",
    "hybrid_search_service",
]