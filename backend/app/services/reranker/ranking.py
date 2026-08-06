"""Cross-Encoder ranking logic."""

import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from app.core.logging import get_logger
from app.services.reranker.model import get_cross_encoder_model, CrossEncoderModel
from app.services.reranker.schemas import (
    RerankerConfig,
    RerankerCandidate,
    RerankedResult,
    RerankerRequest,
    RerankerResponse,
)
from app.services.reranker.exceptions import (
    RerankerError,
    EmptyCandidatesError,
    RerankingError,
    RerankerTimeoutError,
)

logger = get_logger(__name__)


@dataclass
class RerankingResult:
    """Internal result from reranking."""
    chunk_id: str
    document_id: str
    document_name: str
    chunk_index: int
    page: Optional[int]
    section: Optional[str]
    text: str
    hybrid_score: float
    reranker_score: float
    final_score: float
    vector_score: Optional[float]
    bm25_score: Optional[float]
    metadata: Dict[str, Any]


class Reranker:
    """Cross-Encoder re-ranker for improving search result precision."""
    
    def __init__(
        self,
        config: Optional[RerankerConfig] = None,
        model: Optional[CrossEncoderModel] = None,
    ):
        """Initialize the reranker.
        
        Args:
            config: Reranker configuration
            model: Optional pre-initialized CrossEncoderModel
        """
        self._config = config or RerankerConfig()
        self._model = model or get_cross_encoder_model(
            model_name=self._config.model_name,
            cache_dir=self._config.model_cache_dir,
        )
        self._enabled = self._config.enabled
        
    @property
    def is_enabled(self) -> bool:
        """Check if reranker is enabled and available."""
        return self._enabled and self._model.is_loaded()
    
    @property
    def is_available(self) -> bool:
        """Check if model is loaded (regardless of enabled setting)."""
        return self._model.is_loaded()
    
    def enable(self) -> None:
        """Enable the reranker."""
        self._enabled = True
        logger.info("Reranker enabled")
    
    def disable(self) -> None:
        """Disable the reranker."""
        self._enabled = False
        logger.info("Reranker disabled")
    
    def rerank(
        self,
        query: str,
        candidates: List[RerankerCandidate],
        top_k: Optional[int] = None,
    ) -> RerankerResponse:
        """Rerank candidates using Cross-Encoder.
        
        This is the main synchronous interface. For async, use arerank().
        
        Args:
            query: Original search query
            candidates: Candidates from hybrid search
            top_k: Number of results to return (overrides config)
            
        Returns:
            RerankerResponse with reranked results
            
        Raises:
            EmptyCandidatesError: If no candidates provided
            RerankingError: If reranking fails
            RerankerTimeoutError: If timeout exceeded
        """
        # This is a sync wrapper - for production use async version
        import asyncio
        return asyncio.run(self.arerank(query, candidates, top_k))
    
    async def arerank(
        self,
        query: str,
        candidates: List[RerankerCandidate],
        top_k: Optional[int] = None,
    ) -> RerankerResponse:
        """Rerank candidates using Cross-Encoder (async).
        
        Args:
            query: Original search query
            candidates: Candidates from hybrid search
            top_k: Number of results to return (overrides config)
            
        Returns:
            RerankerResponse with reranked results
            
        Raises:
            EmptyCandidatesError: If no candidates provided
            RerankingError: If reranking fails
            RerankerTimeoutError: If timeout exceeded
        """
        start_time = time.time()
        
        # Validate inputs
        if not candidates:
            raise EmptyCandidatesError()
        
        if not query or not query.strip():
            raise RerankingError("Query cannot be empty")
        
        # Use config top_k if not specified
        if top_k is None:
            top_k = self._config.max_results
        
        # Apply candidate limit
        max_candidates = min(len(candidates), self._config.max_candidates)
        candidates = candidates[:max_candidates]
        
        logger.info(
            "Reranking started",
            query=query[:100],
            candidates=len(candidates),
            top_k=top_k,
            enabled=self._enabled,
        )
        
        # If reranker is disabled or model not loaded, return hybrid scores
        if not self._enabled or not self._model.is_loaded():
            logger.warning(
                "Reranker disabled or model not loaded, falling back to hybrid scores",
                enabled=self._enabled,
                model_loaded=self._model.is_loaded(),
            )
            return self._fallback_ranking(query, candidates, top_k, start_time)
        
        try:
            # Prepare query-document pairs for cross-encoder
            pairs = [(query.strip(), candidate.text) for candidate in candidates]
            
            # Run cross-encoder inference with timeout
            scores = await self._run_inference_with_timeout(pairs)
            
            # Combine scores
            results = self._combine_scores(candidates, scores)
            
            # Sort by final score descending
            results.sort(key=lambda r: r.final_score, reverse=True)
            
            # Apply min score threshold
            results = [r for r in results if r.reranker_score >= self._config.min_rerank_score]
            
            # Take top_k
            results = results[:top_k]
            
            reranker_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                "Reranking completed",
                query=query[:100],
                candidates=len(candidates),
                returned=len(results),
                reranker_time_ms=round(reranker_time_ms, 2),
            )
            
            return RerankerResponse(
                results=results,
                reranker_time_ms=reranker_time_ms,
                total_candidates=len(candidates),
                returned_count=len(results),
                fallback=False,
            )
            
        except Exception as e:
            # Check if it's a timeout
            if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                logger.error(f"Reranking timeout: {e}")
                raise RerankerTimeoutError(self._config.timeout_seconds)
            
            logger.error(f"Reranking failed: {e}", exc_info=True)
            # Fall back to hybrid scores on any error
            logger.warning("Reranking failed, falling back to hybrid scores", error=str(e))
            return self._fallback_ranking(query, candidates, top_k, start_time)
    
    async def _run_inference_with_timeout(self, pairs: List[tuple]) -> List[float]:
        """Run cross-encoder inference with timeout."""
        import asyncio
        
        try:
            # Run inference in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            scores = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    self._model.predict,
                    pairs,
                    self._config.batch_size,
                ),
                timeout=self._config.timeout_seconds,
            )
            return scores
        except asyncio.TimeoutError:
            raise RerankerTimeoutError(self._config.timeout_seconds)
    
    def _combine_scores(
        self,
        candidates: List[RerankerCandidate],
        reranker_scores: List[float],
    ) -> List[RerankedResult]:
        """Combine hybrid scores with reranker scores."""
        results = []
        
        for candidate, reranker_score in zip(candidates, reranker_scores):
            # Ensure scores are in [0, 1] range
            hybrid_score = max(0.0, min(1.0, candidate.hybrid_score))
            reranker_score = max(0.0, min(1.0, float(reranker_score)))
            
            # Final score: weighted combination
            # Weight: 40% hybrid, 60% reranker (reranker is more precise)
            final_score = 0.4 * hybrid_score + 0.6 * reranker_score
            
            result = RerankedResult(
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                document_name=candidate.document_name,
                chunk_index=candidate.chunk_index,
                page=candidate.page,
                section=candidate.section,
                text=candidate.text,
                hybrid_score=round(hybrid_score, 4),
                reranker_score=round(reranker_score, 4),
                final_score=round(final_score, 4),
                vector_score=candidate.vector_score,
                bm25_score=candidate.bm25_score,
                metadata={
                    **candidate.metadata,
                    "reranker_model": self._model._model_name,
                },
            )
            results.append(result)
        
        return results
    
    def _fallback_ranking(
        self,
        query: str,
        candidates: List[RerankerCandidate],
        top_k: int,
        start_time: float,
    ) -> RerankerResponse:
        """Fall back to hybrid scores when reranker is unavailable."""
        results = []
        
        for candidate in candidates:
            hybrid_score = max(0.0, min(1.0, candidate.hybrid_score))
            # Use hybrid score as final score when reranker unavailable
            final_score = hybrid_score
            
            result = RerankedResult(
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                document_name=candidate.document_name,
                chunk_index=candidate.chunk_index,
                page=candidate.page,
                section=candidate.section,
                text=candidate.text,
                hybrid_score=round(hybrid_score, 4),
                reranker_score=round(hybrid_score, 4),  # Same as hybrid when fallback
                final_score=round(final_score, 4),
                vector_score=candidate.vector_score,
                bm25_score=candidate.bm25_score,
                metadata={
                    **candidate.metadata,
                    "fallback": True,
                    "fallback_reason": "reranker_unavailable",
                },
            )
            results.append(result)
        
        # Sort by hybrid score
        results.sort(key=lambda r: r.final_score, reverse=True)
        results = results[:top_k]
        
        reranker_time_ms = (time.time() - start_time) * 1000
        
        logger.info(
            "Reranking fallback used",
            query=query[:100],
            candidates=len(candidates),
            returned=len(results),
            fallback=True,
        )
        
        return RerankerResponse(
            results=results,
            reranker_time_ms=reranker_time_ms,
            total_candidates=len(candidates),
            returned_count=len(results),
            fallback=True,
        )
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status of the reranker."""
        model_info = self._model.get_model_info()
        
        return {
            "status": "healthy" if self.is_available else "unavailable",
            "enabled": self._enabled,
            "model_loaded": self._model.is_loaded(),
            "model_name": model_info.get("model_name"),
            "model_device": model_info.get("device"),
            "fallback_mode": not self.is_available,
            "load_error": model_info.get("load_error"),
            "config": {
                "max_candidates": self._config.max_candidates,
                "max_results": self._config.max_results,
                "timeout_seconds": self._config.timeout_seconds,
                "batch_size": self._config.batch_size,
            },
        }


# Singleton instance
reranker = Reranker()