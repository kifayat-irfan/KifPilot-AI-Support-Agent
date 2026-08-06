import time
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.services.retrieval import retrieval_service
from app.services.retrieval.schemas import RetrievalContextRequest, RetrievalFilters
from app.services.rag.answer_generator import AnswerGenerator
from app.services.rag.guardrails import Guardrails
from app.services.rag.prompt_builder import PromptBuilder
from app.services.rag.schemas import (
    RAGAskRequest,
    RAGAskResponse,
    RAGSource,
    RAGHealthResponse,
)
from app.services.rag.exceptions import (
    RAGError,
    EmptyQuestionError,
    PromptInjectionError,
    QuestionTooLongError,
    RetrievalFailedError,
    NoContextFoundError,
    GenerationFailedError,
    OllamaUnavailableError,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.monitoring import (
    record_ai_generation,
    record_retrieval_metrics,
    record_ai_tokens,
    tracer,
)

settings = get_settings()
logger = get_logger(__name__)


class RAGService:
    """Main RAG service orchestrating retrieval, guardrails, and answer generation."""

    DEFAULT_MIN_SCORE = 0.65
    DEFAULT_TOP_K = 5
    DEFAULT_MAX_CONTEXT = 8000

    def __init__(
        self,
        retrieval=None,
        answer_generator=None,
        guardrails=None,
    ):
        self._retrieval = retrieval or retrieval_service
        self._answer_generator = answer_generator or AnswerGenerator()
        self._guardrails = guardrails or Guardrails()
        self._prompt_builder = PromptBuilder()

    async def ask(self, request: RAGAskRequest) -> RAGAskResponse:
        """
        Generate a grounded answer using RAG pipeline.
        
        Pipeline:
        1. Validate question (guardrails)
        2. Generate embedding for question
        3. Retrieve relevant chunks (retrieval engine)
        4. Build context (context builder)
        5. Build prompt (prompt builder)
        6. Generate answer (Ollama)
        7. Calculate confidence
        
        Args:
            request: RAG ask request
            
        Returns:
            RAG answer response
        """
        start_time = time.time()
        retrieval_start = time.time()
        
        # Step 1: Guardrails validation
        try:
            validated_question = self._guardrails.validate_question(request.question)
        except (EmptyQuestionError, PromptInjectionError, QuestionTooLongError):
            raise
        except Exception as e:
            logger.warning("Guardrails validation failed", error=str(e))
            raise RAGError(f"Question validation failed: {str(e)}")

        logger.info(
            "RAG ask started",
            question=validated_question[:100],
            top_k=request.top_k,
            minimum_score=request.minimum_score,
        )

        # Step 2-4: Retrieve and build context
        try:
            # Convert filters
            filters = None
            if request.filters:
                filters = RetrievalFilters(**request.filters)

            context_request = RetrievalContextRequest(
                query=validated_question,
                top_k=request.top_k,
                minimum_score=request.minimum_score,
                filters=filters,
                max_context_chars=self.DEFAULT_MAX_CONTEXT,
            )

            context_response = await self._retrieval.build_context(context_request)

            if not context_response.sources:
                logger.info("No sources found", question=validated_question[:100])
                return RAGAskResponse(
                    answer="I cannot find this information in the indexed documentation.",
                    sources_found=0,
                    response_time_ms=round((time.time() - start_time) * 1000, 2),
                    confidence=0.0,
                    sources=[],
                )

        except Exception as e:
            logger.error("Retrieval failed", error=str(e), question=validated_question[:100])
            raise RetrievalFailedError(str(e))
        
        retrieval_time = time.time() - retrieval_start

        # Step 5-6: Generate answer
        try:
            # Convert sources to RAGSource format
            sources = []
            for s in context_response.sources:
                sources.append(RAGSource(
                    document_id=s.document_id,
                    document_name=s.document_name,
                    chunk_id=s.chunk_id,
                    chunk_index=s.chunk_index,
                    page=s.page,
                    section=s.section,
                    similarity_score=s.similarity_score,
                ))

            # Generate answer
            generation_start = time.time()
            answer = await self._answer_generator.generate(
                question=validated_question,
                context=context_response.context,
                sources=sources,
            )
            generation_time = time.time() - generation_start

            # Calculate confidence
            confidence = self._calculate_confidence(
                sources=sources,
                context_chars=context_response.total_chars,
                answer=answer,
            )

        except OllamaUnavailableError:
            raise
        except GenerationFailedError:
            raise
        except Exception as e:
            logger.error("Answer generation failed", error=str(e), question=validated_question[:100])
            raise GenerationFailedError(str(e))

        total_time_ms = round((time.time() - start_time) * 1000, 2)

        # Record metrics
        try:
            record_retrieval_metrics(
                method="hybrid_rrf_rerank",
                collection="default",
                duration_seconds=retrieval_time,
                result_count=len(sources),
                scores=[s.similarity_score for s in sources] if sources else None,
            )
            
            # Get token counts from answer generator if available
            prompt_tokens = 0
            completion_tokens = 0
            if hasattr(self._answer_generator, '_last_token_usage'):
                prompt_tokens = self._answer_generator._last_token_usage.get('prompt_tokens', 0)
                completion_tokens = self._answer_generator._last_token_usage.get('completion_tokens', 0)
            
            record_ai_generation(
                model=settings.OLLAMA_CHAT_MODEL,
                stream=False,
                duration_seconds=generation_time,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                similarity_score=sum(s.similarity_score for s in sources) / len(sources) if sources else None,
                confidence_score=confidence,
            )
            
            if prompt_tokens > 0 or completion_tokens > 0:
                record_ai_tokens(settings.OLLAMA_CHAT_MODEL, prompt_tokens, completion_tokens)
        except Exception as e:
            logger.warning(f"Failed to record metrics: {e}")

        logger.info(
            "RAG ask completed",
            question=validated_question[:100],
            answer_length=len(answer),
            sources_count=len(sources),
            confidence=round(confidence, 4),
            total_time_ms=total_time_ms,
        )

        return RAGAskResponse(
            answer=answer,
            sources_found=len(sources),
            response_time_ms=total_time_ms,
            confidence=round(confidence, 4),
            sources=sources,
        )

    def _calculate_confidence(
        self,
        sources: List[RAGSource],
        context_chars: int,
        answer: str,
    ) -> float:
        """
        Calculate confidence score (0-1) based on:
        - Average similarity score (40%)
        - Retrieved chunk count (20%)
        - Context completeness (20%)
        - Answer specificity (20%)
        """
        if not sources:
            return 0.0

        # Average similarity score
        avg_similarity = sum(s.similarity_score for s in sources) / len(sources)

        # Chunk count factor (more chunks = more evidence, up to 5)
        chunk_factor = min(len(sources) / 5.0, 1.0)

        # Context completeness (relative to max)
        context_factor = min(context_chars / self.DEFAULT_MAX_CONTEXT, 1.0)

        # Answer specificity (not the "I cannot find" response)
        unknown_phrase = "I cannot find this information in the indexed documentation"
        specificity = 0.0 if answer.strip() == unknown_phrase else 1.0

        # Weighted composite
        confidence = (
            0.4 * avg_similarity +
            0.2 * chunk_factor +
            0.2 * context_factor +
            0.2 * specificity
        )

        return max(0.0, min(1.0, confidence))

    async def health_check(self) -> RAGHealthResponse:
        """Check health of RAG system dependencies."""
        try:
            retrieval_health = await self._retrieval.health_check()
            ollama_health = await self._answer_generator.health_check()

            retrieval_healthy = retrieval_health.status == "healthy"
            ollama_healthy = ollama_health

            overall_healthy = retrieval_healthy and ollama_healthy

            return RAGHealthResponse(
                status="healthy" if overall_healthy else "unhealthy",
                retrieval_service_healthy=retrieval_healthy,
                ollama_service_healthy=ollama_healthy,
            )
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return RAGHealthResponse(
                status="unhealthy",
                retrieval_service_healthy=False,
                ollama_service_healthy=False,
                error=str(e),
            )


# Singleton instance
rag_service = RAGService()