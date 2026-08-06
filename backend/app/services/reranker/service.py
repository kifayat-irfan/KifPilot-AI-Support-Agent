"""Main Reranker Service integrating with Hybrid Search pipeline."""

import time
import logging
from typing import List, Optional, Dict, Any, Tuple

from app.services.hybrid_search import hybrid_search_service
from app.services.hybrid_search.schemas import HybridSearchRequest, HybridSearchResult, HybridSearchFilters
from app.services.reranker.ranking import Reranker, RerankerConfig
from app.services.reranker.schemas import (
    RerankedResult,
    RerankerRequest,
    RerankerResponse,
    RerankerHealthResponse,
)
from app.services.reranker.exceptions import (
    RerankerError,
    EmptyCandidatesError,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.monitoring import ai_reranker_time

settings = get_settings()
logger = get_logger(__name__)


class RerankerService:
    """Reranker service integrated with hybrid search pipeline."""

    def __init__(
        self,
        reranker: Optional[Reranker] = None,
        hybrid_search=None,
    ):
        self._reranker = reranker or Reranker()
        self._hybrid_search = hybrid_search or hybrid_search_service
        self._enabled = getattr(settings, 'RERANKER_ENABLED', False)
        self._max_candidates = getattr(settings, 'RERANKER_MAX_CANDIDATES', 20)
        self._max_results = getattr(settings, 'RERANKER_MAX_RESULTS', 5)

    @property
    def is_enabled(self) -> bool:
        """Check if reranker is enabled."""
        return self._enabled and self._reranker.is_available

    @property
    def is_available(self) -> bool:
        """Check if reranker model is loaded."""
        return self._reranker.is_available

    async def search_and_rerank(
        self,
        request: HybridSearchRequest,
        organization_id: Optional[str] = None,
        rerank_top_k: Optional[int] = None,
    ) -> Tuple[List[RerankedResult], Dict[str, Any]]:
        """
        Perform hybrid search followed by cross-encoder reranking.
        
        Pipeline:
        1. Hybrid Search (Vector + BM25 + RRF) -> Top 20 candidates
        2. Cross-Encoder Reranking -> Top 5 results
        
        Args:
            request: Hybrid search request
            organization_id: Optional organization ID
            rerank_top_k: Number of results to return after reranking
            
        Returns:
            Tuple of (reranked_results, timing_info)
        """
        total_start = time.time()
        
        # Step 1: Hybrid Search
        hybrid_start = time.time()
        
        # Create modified request for hybrid search to get more candidates
        hybrid_request = HybridSearchRequest(
            query=request.query,
            top_k=self._max_candidates,  # Get more candidates for reranking
            minimum_score=request.minimum_score,
            rrf_constant=request.rrf_constant,
            vector_weight=request.vector_weight,
            bm25_weight=request.bm25_weight,
            filters=request.filters,
            include_vector_scores=request.include_vector_scores,
            include_bm25_scores=request.include_bm25_scores,
        )
        
        hybrid_response = await self._hybrid_search.search(
            request=hybrid_request,
            organization_id=organization_id,
        )
        
        hybrid_time_ms = (time.time() - hybrid_start) * 1000
        
        if not hybrid_response.results:
            logger.info("Hybrid search returned no results, skipping reranking")
            return [], {
                "hybrid_time_ms": hybrid_time_ms,
                "reranker_time_ms": 0,
                "total_time_ms": (time.time() - total_start) * 1000,
                "fallback": False,
                "candidates_count": 0,
            }
        
        # Step 2: Convert to reranker candidates
        candidates = self._convert_to_candidates(hybrid_response.results)
        
        # Step 3: Rerank
        reranker_start = time.time()
        
        if self._enabled and self._reranker.is_available:
            reranker_request = RerankerRequest(
                query=request.query.strip(),
                candidates=candidates,
                top_k=rerank_top_k or self._max_results,
            )
            
            try:
                reranker_response = await self._reranker.arerank(
                    query=request.query.strip(),
                    candidates=candidates,
                    top_k=rerank_top_k or self._max_results,
                )
                reranked_results = reranker_response.results
                fallback = reranker_response.fallback
            except Exception as e:
                logger.warning(f"Reranking failed, falling back to hybrid scores: {e}")
                reranked_results = self._fallback_to_hybrid(candidates, rerank_top_k or self._max_results)
                fallback = True
        else:
            # Reranker disabled or model not loaded
            logger.info("Reranker disabled or model not loaded, using hybrid scores")
            reranked_results = self._fallback_to_hybrid(candidates, rerank_top_k or self._max_results)
            fallback = True
        
        reranker_time_ms = (time.time() - reranker_start) * 1000
        total_time_ms = (time.time() - total_start) * 1000
        
        # Record reranker metrics
        try:
            ai_reranker_time.labels(model="cross-encoder", candidate_count=str(len(candidates))).observe(reranker_time_ms / 1000)
        except Exception as e:
            logger.warning(f"Failed to record reranker metrics: {e}")

        logger.info(
            "Search and rerank completed",
            query=request.query[:100],
            candidates=len(candidates),
            reranked=len(reranked_results),
            hybrid_time_ms=round(hybrid_time_ms, 2),
            reranker_time_ms=round(reranker_time_ms, 2),
            total_time_ms=round(total_time_ms, 2),
            fallback=fallback,
        )
        
        timing_info = {
            "hybrid_time_ms": round(hybrid_time_ms, 2),
            "reranker_time_ms": round(reranker_time_ms, 2),
            "total_time_ms": round(total_time_ms, 2),
            "fallback": fallback,
            "candidates_count": len(candidates),
        }
        
        return reranked_results, timing_info
    
    def _convert_to_candidates(self, hybrid_results: List[HybridSearchResult]) -> List:
        """Convert hybrid search results to reranker candidates."""
        from app.services.reranker.schemas import RerankerCandidate
        
        candidates = []
        for result in hybrid_results:
            candidate = RerankerCandidate(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                document_name=result.document_name,
                chunk_index=result.chunk_index,
                page=result.page,
                section=result.section,
                text=result.text,
                hybrid_score=result.rrf_score,
                vector_score=result.vector_score,
                bm25_score=result.bm25_score,
                metadata=result.metadata,
            )
            candidates.append(candidate)
        
        return candidates
    
    def _fallback_to_hybrid(self, candidates: List, top_k: Optional[int] = None) -> List[RerankedResult]:
        """Fall back to hybrid scores when reranker unavailable."""
        from app.services.reranker.schemas import RerankedResult
        
        results = []
        for candidate in candidates:
            hybrid_score = max(0.0, min(1.0, candidate.hybrid_score))
            result = RerankedResult(
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                document_name=candidate.document_name,
                chunk_index=candidate.chunk_index,
                page=candidate.page,
                section=candidate.section,
                text=candidate.text,
                hybrid_score=round(hybrid_score, 4),
                reranker_score=round(hybrid_score, 4),  # Use hybrid score as reranker score
                final_score=round(hybrid_score, 4),
                vector_score=candidate.vector_score,
                bm25_score=candidate.bm25_score,
                metadata={
                    **candidate.metadata,
                    "fallback": True,
                    "fallback_reason": "reranker_disabled_or_unavailable",
                },
            )
            results.append(result)
        
        # Sort by hybrid score and take top_k
        results.sort(key=lambda r: r.final_score, reverse=True)
        return results[:top_k] if top_k else results

    async def rerank_context(
        self,
        query: str,
        candidates: List,
        top_k: int = 5,
    ) -> List[RerankedResult]:
        """Rerank candidates for context building (used by RetrievalService.build_context)."""
        if not self._enabled or not self._reranker.is_available:
            # Fallback to hybrid scores
            return self._fallback_to_hybrid(candidates, top_k)
        
        import time
        start_time = time.time()
        
        try:
            reranked = await self._reranker.arerank(
                query=query.strip(),
                candidates=candidates,
                top_k=top_k,
            )
            
            # Record metrics
            try:
                ai_reranker_time.labels(model="cross-encoder", candidate_count=str(len(candidates))).observe(time.time() - start_time)
            except Exception as e:
                logger.warning(f"Failed to record reranker metrics: {e}")
            
            return reranked.results
        except Exception as e:
            logger.warning(f"Context reranking failed: {e}, using hybrid scores")
            return self._fallback_to_hybrid(candidates, top_k)

    async def health_check(self) -> RerankerHealthResponse:
        """Check health of reranker service."""
        try:
            health = self._reranker.get_health()
            
            return RerankerHealthResponse(
                status=health.get("status", "unavailable"),
                model_loaded=health.get("model_loaded", False),
                model_name=health.get("model_name"),
                model_device=health.get("model_device"),
                fallback_mode=health.get("fallback_mode", False),
                error=health.get("error"),
            )
        except Exception as e:
            logger.error(f"Reranker health check failed: {e}")
            return RerankerHealthResponse(
                status="unhealthy",
                model_loaded=False,
                fallback_mode=True,
                error=str(e),
            )


# Singleton instance
reranker_service = RerankerService()