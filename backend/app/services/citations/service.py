import time
from typing import List, Optional, Dict, Any

from app.services.retrieval import retrieval_service
from app.services.retrieval.schemas import RetrievalContextRequest, RetrievalFilters
from app.services.rag import rag_service
from app.services.rag.schemas import RAGAskRequest
from app.services.citations.schemas import CitedAnswer, Citation
from app.services.citations.formatter import CitationBuilder, CitationDeduplicator, CitationFormatter
from app.services.citations.validator import CitationValidator, CitationEnricher
from app.services.citations.exceptions import (
    CitationError,
    MissingChunkError,
    DeletedDocumentError,
    InvalidMetadataError,
    CitationGenerationError,
    CitationValidationError,
)
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


class CitationService:
    """Main citation service orchestrating RAG + citation generation."""

    def __init__(
        self,
        retrieval=None,
        rag=None,
        validator=None,
        formatter=None,
    ):
        self._retrieval = retrieval or retrieval_service
        self._rag = rag or rag_service
        self._validator = validator or CitationValidator()
        self._formatter = formatter or CitationFormatter()

    async def ask_with_citations(
        self,
        question: str,
        top_k: int = 5,
        minimum_score: float = 0.65,
        filters: Optional[Dict[str, Any]] = None,
    ) -> CitedAnswer:
        """
        Generate answer with full citations.
        
        Pipeline:
        1. Retrieve relevant context
        2. Generate answer using RAG
        3. Build citations from sources
        4. Validate and deduplicate citations
        5. Format final response
        
        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            minimum_score: Minimum similarity threshold
            filters: Optional metadata filters
            
        Returns:
            CitedAnswer with answer, citations, confidence
        """
        start_time = time.time()

        # Step 1: Retrieve context using retrieval engine
        logger.info("Citation ask started", question=question[:100])

        try:
            retrieval_request = RetrievalContextRequest(
                query=question,
                top_k=top_k,
                minimum_score=minimum_score,
                filters=RetrievalFilters(**filters) if filters else None,
                max_context_chars=8000,
            )
            context_response = await self._retrieval.build_context(retrieval_request)
            
            if not context_response.sources:
                logger.info("No sources found", question=question[:100])
                return CitedAnswer(
                    answer="I cannot find this information in the indexed documentation.",
                    citations=[],
                    confidence=0.0,
                    sources_found=0,
                    response_time_ms=round((time.time() - start_time) * 1000, 2),
                )

        except Exception as e:
            logger.error("Retrieval failed", error=str(e))
            raise CitationGenerationError(f"Retrieval failed: {str(e)}")

        # Step 2: Generate answer using RAG
        try:
            rag_request = RAGAskRequest(
                question=question,
                top_k=top_k,
                minimum_score=minimum_score,
                filters=filters,
            )
            rag_response = await self._rag.ask(rag_request)
            
            answer = rag_response.answer
            
        except Exception as e:
            logger.error("RAG generation failed", error=str(e))
            raise CitationGenerationError(f"Answer generation failed: {str(e)}")

        # Step 3: Build citations from sources
        citations = CitationBuilder.from_rag_sources(context_response.sources)
        
        if not citations:
            logger.info("No citations generated", question=question[:100])
            return CitedAnswer(
                answer=answer,
                citations=[],
                confidence=rag_response.confidence,
                sources_found=0,
                response_time_ms=round((time.time() - start_time) * 1000, 2),
            )

        # Step 4: Validate citations
        validator = CitationValidator()
        citations = validator.filter_valid(citations)
        
        # Step 5: Deduplicate and sort
        citations = CitationDeduplicator.deduplicate(citations)
        citations = CitationDeduplicator.sort_by_score(citations)
        
        # Step 6: Enrich with confidence ranking
        citations = CitationEnricher.add_confidence_ranking(citations)

        # Step 7: Calculate overall confidence
        confidence = rag_response.confidence

        total_time_ms = round((time.time() - start_time) * 1000, 2)

        logger.info(
            "Citation ask completed",
            question=question[:100],
            answer_length=len(answer),
            citations_count=len(citations),
            confidence=round(confidence, 4),
            total_time_ms=total_time_ms,
        )

        return CitedAnswer(
            answer=answer,
            citations=citations,
            confidence=confidence,
            sources_found=len(citations),
            response_time_ms=total_time_ms,
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check health of citation service dependencies."""
        try:
            retrieval_health = await self._retrieval.health_check()
            rag_health = await self._rag.health_check()
            
            # HealthCheckResponse objects have attributes, not dict-like access
            retrieval_healthy = (
                getattr(retrieval_health, "vector_store_connected", False) and
                getattr(retrieval_health, "embedding_service_available", False)
            )
            rag_healthy = getattr(rag_health, "status", "") == "healthy"
            
            overall = retrieval_healthy and rag_healthy
            
            return {
                "status": "healthy" if overall else "unhealthy",
                "citation_service_healthy": True,
                "retrieval_service_healthy": retrieval_healthy,
                "rag_service_healthy": rag_healthy,
            }
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return {
                "status": "unhealthy",
                "citation_service_healthy": False,
                "retrieval_service_healthy": False,
                "rag_service_healthy": False,
                "error": str(e),
            }


# Singleton instance
citation_service = CitationService()