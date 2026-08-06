"""Main hybrid search service combining vector and BM25 search."""

import time
import logging
from typing import List, Optional, Dict, Any, Tuple

from app.services.retrieval.search import RetrievalSearcher
from app.services.retrieval.ranking import RetrievalRanker
from app.services.vectorstore import vector_store_service
from app.services.vectorstore.models import SearchResult
from app.services.hybrid_search.bm25 import bm25_indexer, BM25Indexer
from app.services.hybrid_search.fusion import (
    reciprocal_rank_fusion,
    normalize_scores,
    deduplicate_results,
)
from app.services.hybrid_search.schemas import (
    HybridSearchRequest,
    HybridSearchResponse,
    HybridSearchResult,
    HybridSearchHealthResponse,
    HybridSearchFilters,
)
from app.services.hybrid_search.exceptions import (
    HybridSearchError,
    EmptyQueryError,
    InvalidTopKError,
    InvalidRRFConstantError,
    InvalidWeightError,
    VectorSearchError,
    BM25SearchError,
    FusionError,
    EmbeddingGenerationError,
)
from app.services.retrieval.schemas import RetrievalFilters
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class HybridSearchService:
    """Hybrid search service combining vector and BM25 search with RRF fusion."""

    def __init__(
        self,
        vector_searcher: Optional[RetrievalSearcher] = None,
        bm25_indexer_instance: Optional[BM25Indexer] = None,
        ranker: Optional["RetrievalRanker"] = None,
    ):
        self._vector_searcher = vector_searcher or RetrievalSearcher()
        self._bm25_indexer = bm25_indexer_instance or bm25_indexer
        self._ranker = ranker or RetrievalRanker()
        self._default_min_score = getattr(settings, 'RETRIEVAL_MIN_SCORE', 0.3)
        self._default_rrf_k = getattr(settings, 'HYBRID_RRF_K', 60)

    async def search(
        self,
        request: HybridSearchRequest,
        organization_id: Optional[str] = None,
    ) -> HybridSearchResponse:
        """
        Perform hybrid search combining vector and BM25 search.
        
        Args:
            request: Hybrid search request
            organization_id: Optional organization ID for multi-tenant isolation
            
        Returns:
            Hybrid search response with fused results
        """
        start_time = time.time()

        # Validate query
        if not request.query or not request.query.strip():
            raise EmptyQueryError()

        # Validate top_k
        if request.top_k < 1 or request.top_k > 20:
            raise InvalidTopKError(request.top_k)

        # Validate RRF constant
        if request.rrf_constant < 1 or request.rrf_constant > 1000:
            raise InvalidRRFConstantError(request.rrf_constant)

        # Validate weights
        if request.vector_weight < 0.0 or request.vector_weight > 2.0:
            raise InvalidWeightError("vector_weight", request.vector_weight)
        if request.bm25_weight < 0.0 or request.bm25_weight > 2.0:
            raise InvalidWeightError("bm25_weight", request.bm25_weight)

        logger.info(
            "Hybrid search started",
            query=request.query[:100],
            top_k=request.top_k,
            rrf_constant=request.rrf_constant,
            vector_weight=request.vector_weight,
            bm25_weight=request.bm25_weight,
            organization_id=organization_id,
        )

        # Execute vector and BM25 search in parallel
        vector_results, vector_time_ms = await self._vector_search(
            query=request.query.strip(),
            top_k=request.top_k,
            minimum_score=request.minimum_score,
            filters=request.filters,
            organization_id=organization_id,
        )

        bm25_results, bm25_time_ms = self._bm25_search(
            query=request.query.strip(),
            top_k=request.top_k,
            minimum_score=request.minimum_score,
            organization_id=organization_id,
            document_ids=request.filters.document_id if request.filters else None,
        )

        # Fuse results
        fusion_start = time.time()
        fused_results = self._fuse_results(
            vector_results=vector_results,
            bm25_results=bm25_results,
            rrf_k=request.rrf_constant,
            vector_weight=request.vector_weight,
            bm25_weight=request.bm25_weight,
            top_k=request.top_k,
            include_vector_scores=request.include_vector_scores,
            include_bm25_scores=request.include_bm25_scores,
        )
        fusion_time_ms = (time.time() - fusion_start) * 1000

        total_time_ms = (time.time() - start_time) * 1000

        logger.info(
            "Hybrid search completed",
            query=request.query[:100],
            results_count=len(fused_results),
            vector_time_ms=round(vector_time_ms, 2),
            bm25_time_ms=round(bm25_time_ms, 2),
            fusion_time_ms=round(fusion_time_ms, 2),
            total_time_ms=round(total_time_ms, 2),
            organization_id=organization_id,
        )

        return HybridSearchResponse(
            search_time_ms=round(total_time_ms, 2),
            vector_search_time_ms=round(vector_time_ms, 2),
            bm25_search_time_ms=round(bm25_time_ms, 2),
            fusion_time_ms=round(fusion_time_ms, 2),
            total_results=len(fused_results),
            results=fused_results,
        )

    async def _vector_search(
        self,
        query: str,
        top_k: int,
        minimum_score: float,
        filters: Optional[HybridSearchFilters] = None,
        organization_id: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Execute vector search and return formatted results."""
        try:
            # Convert filters
            retrieval_filters = None
            if filters:
                retrieval_filters = RetrievalFilters(
                    company=filters.company,
                    category=filters.category,
                    language=filters.language,
                    document_id=filters.document_id,
                    file_type=filters.file_type,
                    processing_status=filters.processing_status,
                    created_after=filters.created_after,
                    created_before=filters.created_before,
                )

            # Execute vector search
            raw_results, search_time_ms = await self._vector_searcher.search(
                query=query,
                top_k=top_k,
                minimum_score=minimum_score,
                filters=retrieval_filters,
                organization_id=organization_id,
            )

            # Rank results
            ranked_results = self._ranker.rank_results(raw_results, top_k=top_k)

            # Format for fusion
            formatted = []
            for result in ranked_results:
                metadata = result.metadata or {}
                formatted.append({
                    "chunk_id": result.id,
                    "document_id": metadata.get("document_id", ""),
                    "document_name": metadata.get("document_name", "Unknown"),
                    "chunk_index": metadata.get("chunk_index", 0),
                    "page": metadata.get("page"),
                    "section": metadata.get("section"),
                    "text": result.document,
                    "score": metadata.get("composite_score", result.score),
                    "vector_score": result.score,
                    "rank": 0,  # Will be set during fusion
                    "metadata": metadata,
                })

            return formatted, search_time_ms

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise VectorSearchError(f"Vector search failed: {str(e)}")

    def _bm25_search(
        self,
        query: str,
        top_k: int,
        minimum_score: float,
        organization_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Execute BM25 search and return formatted results."""
        start_time = time.time()

        try:
            # Use BM25 indexer to search
            bm25_results = self._bm25_indexer.search(
                query=query,
                top_k=top_k,
                minimum_score=minimum_score,
                filter_document_ids=document_ids,
            )

            # Format results
            formatted = []
            for doc, score in bm25_results:
                metadata = doc.metadata or {}
                formatted.append({
                    "chunk_id": doc.chunk_id,
                    "document_id": doc.document_id,
                    "document_name": doc.document_name,
                    "chunk_index": metadata.get("chunk_index", 0),
                    "page": metadata.get("page"),
                    "section": metadata.get("section"),
                    "text": doc.text,
                    "score": score,  # Raw BM25 score
                    "bm25_score": score,
                    "rank": 0,
                    "metadata": metadata,
                })

            search_time_ms = (time.time() - start_time) * 1000
            return formatted, search_time_ms

        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            raise BM25SearchError(f"BM25 search failed: {str(e)}")

    def _fuse_results(
        self,
        vector_results: List[Dict[str, Any]],
        bm25_results: List[Dict[str, Any]],
        rrf_k: int,
        vector_weight: float,
        bm25_weight: float,
        top_k: int,
        include_vector_scores: bool,
        include_bm25_scores: bool,
    ) -> List[HybridSearchResult]:
        """Fuse vector and BM25 results using RRF."""
        try:
            # Assign ranks
            for i, r in enumerate(vector_results):
                r["rank"] = i + 1
            for i, r in enumerate(bm25_results):
                r["rank"] = i + 1

            # Apply RRF fusion
            fused = reciprocal_rank_fusion(
                vector_results=vector_results,
                bm25_results=bm25_results,
                k=rrf_k,
                vector_weight=vector_weight,
                bm25_weight=bm25_weight,
            )

            # Take top_k
            fused = fused[:top_k]

            # Convert to response format
            results = []
            for item in fused:
                metadata = item.get("metadata", {})
                
                # Calculate normalized BM25 score
                raw_bm25 = item.get("bm25_score", 0.0)
                normalized_bm25 = min(max(raw_bm25 / 10.0, 0.0), 1.0)  # Rough normalization

                result = HybridSearchResult(
                    document_id=item.get("document_id", ""),
                    document_name=item.get("document_name", "Unknown"),
                    chunk_id=item.get("chunk_id", ""),
                    chunk_index=item.get("chunk_index", 0),
                    page=item.get("page"),
                    section=item.get("section"),
                    text=item.get("text", ""),
                    rrf_score=round(item.get("rrf_score", 0.0), 4),
                    vector_score=round(item.get("vector_score"), 4) if include_vector_scores and item.get("vector_score") is not None else None,
                    bm25_score=round(item.get("bm25_score"), 4) if include_bm25_scores and item.get("bm25_score") is not None else None,
                    normalized_bm25_score=round(normalized_bm25, 4) if include_bm25_scores else None,
                    metadata={
                        "vector_rank": item.get("vector_rank"),
                        "bm25_rank": item.get("bm25_rank"),
                        "quality_score": metadata.get("quality_score"),
                        "freshness_score": metadata.get("freshness_score"),
                        "composite_score": metadata.get("composite_score"),
                        "file_type": metadata.get("file_type"),
                        "language": metadata.get("language"),
                        "category": metadata.get("category"),
                        "company": metadata.get("company"),
                        "created_at": metadata.get("created_at"),
                    },
                )
                results.append(result)

            return results

        except Exception as e:
            logger.error(f"Rank fusion failed: {e}")
            raise FusionError(f"Rank fusion failed: {str(e)}")

    async def build_bm25_index(
        self,
        organization_id: Optional[str] = None,
        batch_size: int = 100,
    ) -> Dict[str, Any]:
        """
        Build or rebuild BM25 index from vector store.
        
        Args:
            organization_id: Optional organization ID to filter chunks
            batch_size: Number of chunks to process per batch
            
        Returns:
            Index build statistics
        """
        try:
            start_time = time.time()
            count = await self._bm25_indexer.rebuild_index(
                vector_store=vector_store_service,
                organization_id=organization_id,
                batch_size=batch_size,
            )
            
            build_time_ms = (time.time() - start_time) * 1000
            
            return {
                "indexed_count": count,
                "build_time_ms": round(build_time_ms, 2),
                "status": "completed",
            }
        except Exception as e:
            logger.error(f"BM25 index build failed: {e}")
            raise BM25IndexBuildError(f"BM25 index build failed: {str(e)}")

    async def add_document_to_bm25(
        self,
        chunk_id: str,
        document_id: str,
        document_name: str,
        text: str,
        metadata: Dict[str, Any],
    ) -> None:
        """Add a document to the BM25 index."""
        self._bm25_indexer.add_document(
            chunk_id=chunk_id,
            document_id=document_id,
            document_name=document_name,
            text=text,
            metadata=metadata,
        )
        self._bm25_indexer.save_index()

    async def remove_document_from_bm25(self, chunk_id: str) -> bool:
        """Remove a document from the BM25 index."""
        removed = self._bm25_indexer.remove_document(chunk_id)
        if removed:
            self._bm25_indexer.save_index()
        return removed

    async def health_check(self, organization_id: Optional[str] = None) -> HybridSearchHealthResponse:
        """Check health of hybrid search system."""
        try:
            # Check vector store and embedding service
            vector_health = await self._vector_searcher.health_check(organization_id)
            
            # Check BM25 index
            bm25_stats = self._bm25_indexer.get_index_stats()
            bm25_loaded = bm25_stats["total_documents"] > 0
            
            overall_healthy = (
                vector_health.get("vector_store_connected", False) and
                vector_health.get("embedding_service_available", False) and
                bm25_loaded
            )

            return HybridSearchHealthResponse(
                status="healthy" if overall_healthy else "degraded",
                vector_store_connected=vector_health.get("vector_store_connected", False),
                embedding_service_available=vector_health.get("embedding_service_available", False),
                bm25_index_loaded=bm25_loaded,
                bm25_index_chunk_count=bm25_stats["total_documents"],
                bm25_last_updated=bm25_stats.get("last_updated"),
            )
        except Exception as e:
            logger.error(f"Hybrid health check failed: {e}")
            return HybridSearchHealthResponse(
                status="unhealthy",
                vector_store_connected=False,
                embedding_service_available=False,
                bm25_index_loaded=False,
                bm25_index_chunk_count=0,
                error=str(e),
            )


# Singleton instance
hybrid_search_service = HybridSearchService()