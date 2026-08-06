"""Streaming chat service using SSE for real-time token streaming."""

import time
import asyncio
from typing import List, Optional, Dict, Any, AsyncGenerator
from datetime import datetime

from app.services.retrieval import retrieval_service
from app.services.retrieval.schemas import RetrievalContextRequest, RetrievalFilters
from app.services.citations import citation_service
from app.services.citations.schemas import Citation
from app.services.citations.formatter import CitationBuilder
from app.services.rag import rag_service
from app.services.rag.schemas import RAGAskRequest, RAGSource
from app.services.llm import ollama_service
from app.services.llm.models import ChatCompletionRequest, ChatMessage, ModelRole
from app.services.streaming.schemas import (
    StreamChatRequest,
    StreamStartEvent,
    StreamRetrievalEvent,
    StreamTokenEvent,
    StreamCitationsEvent,
    StreamCompleteEvent,
    StreamErrorEvent,
    StreamHealthResponse,
)
from app.services.streaming.events import SSEFormatter
from app.services.streaming.exceptions import (
    StreamingError,
    RetrievalFailedError,
    NoContextFoundError,
    GenerationFailedError,
    OllamaUnavailableError,
    CitationGenerationError,
    StreamingTimeoutError,
    ClientDisconnectedError,
    GuardrailsError,
)
from app.services.rag.guardrails import Guardrails
from app.core.config import get_settings
from app.core.logging import get_logger
from app.monitoring import (
    record_ai_generation,
    record_retrieval_metrics,
    record_ai_tokens,
    ai_streaming_duration,
)

settings = get_settings()
logger = get_logger(__name__)


class StreamingService:
    """Streaming chat service using SSE for real-time token streaming."""
    
    DEFAULT_TIMEOUT_SECONDS = 120
    DEFAULT_TOP_K = 5
    DEFAULT_MIN_SCORE = 0.65
    DEFAULT_MAX_CONTEXT = 8000
    
    def __init__(
        self,
        retrieval=None,
        rag=None,
        ollama=None,
        citations=None,
        guardrails=None,
    ):
        self._retrieval = retrieval or retrieval_service
        self._rag = rag or rag_service
        self._ollama = ollama or ollama_service
        self._citations = citations or citation_service
        self._guardrails = guardrails or Guardrails()
        self._formatter = SSEFormatter()
    
    async def stream_chat(
        self,
        request: StreamChatRequest,
    ) -> AsyncGenerator[str, None]:
        """
        Stream chat response using SSE.
        
        Pipeline:
        1. Emit start event
        2. Retrieve relevant context (emit retrieval event)
        3. Build citations from sources
        4. Generate answer with token streaming (emit token events)
        5. Emit citations event
        6. Emit completion event
        
        Args:
            request: Streaming chat request
            
        Yields:
            SSE-formatted event strings
        """
        start_time = time.time()
        token_count = 0
        client_disconnected = False
        retrieval_time = 0
        generation_time = 0
        
        try:
            # Step 0: Emit start event
            yield self._formatter.format_start()
            
            # Step 1: Retrieve context
            logger.info(
                "Streaming chat started",
                question=request.question[:100],
                top_k=request.top_k,
                minimum_score=request.minimum_score,
            )
            
            retrieval_start = time.time()
            try:
                retrieval_request = RetrievalContextRequest(
                    query=request.question,
                    top_k=request.top_k,
                    minimum_score=request.minimum_score,
                    filters=RetrievalFilters(**request.filters) if request.filters else None,
                    max_context_chars=self.DEFAULT_MAX_CONTEXT,
                )
                context_response = await self._retrieval.build_context(retrieval_request)
                
                retrieval_time = time.time() - retrieval_start
                
                if not context_response.sources:
                    logger.info("No sources found", question=request.question[:100])
                    yield self._formatter.format_error(
                        "I cannot find this information in the indexed documentation.",
                        "NO_CONTEXT_FOUND"
                    )
                    return
                
                # Emit retrieval event
                yield self._formatter.format_retrieval(
                    chunks_found=len(context_response.sources),
                    search_time_ms=context_response.search_time_ms
                )
                
            except Exception as e:
                logger.error("Retrieval failed", error=str(e), question=request.question[:100])
                yield self._formatter.format_error(
                    f"Retrieval failed: {str(e)}",
                    "RETRIEVAL_FAILED"
                )
                return
            
            # Step 2: Build citations from sources
            citations = CitationBuilder.from_rag_sources(context_response.sources)
            
            if not citations:
                logger.info("No citations generated", question=request.question[:100])
                yield self._formatter.format_error(
                    "No valid citations could be generated",
                    "CITATION_GENERATION_FAILED"
                )
                return
            
            # Step 3: Generate answer with streaming
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
                
                # Build prompt
                from app.services.rag.prompt_builder import PromptBuilder
                prompt_messages = PromptBuilder.build_prompt_with_sources(
                    request.question,
                    context_response.context,
                    sources
                )
                
                # Create chat completion request with streaming
                chat_request = ChatCompletionRequest(
                    messages=[ChatMessage(role=ModelRole(m["role"]), content=m["content"]) for m in prompt_messages],
                    model=settings.OLLAMA_CHAT_MODEL,
                    temperature=0.0,
                    top_p=1.0,
                    max_tokens=2048,
                    stream=True,
                )
                
                # Stream tokens from Ollama
                answer_parts = []
                
                generation_start = time.time()
                
                try:
                    stream = await asyncio.wait_for(
                        self._ollama.chat_stream(chat_request),
                        timeout=self.DEFAULT_TIMEOUT_SECONDS
                    )
                    
                    async for chunk in stream:
                        if chunk.message.content:
                            text = chunk.message.content
                            answer_parts.append(text)
                            token_count += 1
                            yield self._formatter.format_token(text)
                            
                            if chunk.done:
                                break
                                
                except asyncio.TimeoutError:
                    raise StreamingTimeoutError(self.DEFAULT_TIMEOUT_SECONDS)
                
                generation_time = time.time() - generation_start
                full_answer = "".join(answer_parts)
                
                if not full_answer.strip():
                    full_answer = "I cannot find this information in the indexed documentation."
                
                # Step 4: Emit citations
                citation_data = []
                for citation in citations:
                    citation_data.append({
                        "document_id": citation.document_id,
                        "document_name": citation.document_name,
                        "page_number": citation.page_number,
                        "section": citation.section,
                        "chunk_id": citation.chunk_id,
                        "chunk_index": citation.chunk_index,
                        "similarity_score": citation.similarity_score,
                    })
                
                yield self._formatter.format_citations(citation_data)
                
                # Step 5: Calculate confidence
                confidence = rag_service._calculate_confidence(
                    sources=sources,
                    context_chars=context_response.total_chars,
                    answer=full_answer,
                )
                
                # Step 5: Emit completion
                total_time_ms = round((time.time() - start_time) * 1000, 2)
                
                logger.info(
                    "Streaming chat completed",
                    question=request.question[:100],
                    answer_length=len(full_answer),
                    token_count=token_count,
                    citations_count=len(citations),
                    confidence=round(confidence, 4),
                    total_time_ms=total_time_ms,
                )
                
                yield self._formatter.format_complete(
                    confidence=confidence,
                    sources_found=len(citations),
                    response_time_ms=total_time_ms
                )
                
                # Record metrics
                try:
                    record_retrieval_metrics(
                        method="hybrid_rrf_rerank",
                        collection="default",
                        duration_seconds=retrieval_time,
                        result_count=len(sources),
                        scores=[s.similarity_score for s in sources] if sources else None,
                    )
                    
                    # Get token counts from response
                    prompt_tokens = getattr(chunk, 'prompt_eval_count', 0) if 'chunk' in locals() else 0
                    completion_tokens = getattr(chunk, 'eval_count', 0) if 'chunk' in locals() else 0
                    
                    record_ai_generation(
                        model=settings.OLLAMA_CHAT_MODEL,
                        stream=True,
                        duration_seconds=generation_time,
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens,
                        similarity_score=sum(s.similarity_score for s in sources) / len(sources) if sources else None,
                        confidence_score=confidence,
                    )
                    
                    record_ai_tokens(settings.OLLAMA_CHAT_MODEL, prompt_tokens, completion_tokens)
                    
                    ai_streaming_duration.labels(model=settings.OLLAMA_CHAT_MODEL).observe(generation_time)
                except Exception as e:
                    logger.warning(f"Failed to record streaming metrics: {e}")
                
            except (OllamaUnavailableError, GenerationFailedError, StreamingTimeoutError):
                raise
            except Exception as e:
                logger.error("Streaming generation failed", error=str(e), question=request.question[:100])
                raise GenerationFailedError(str(e))
                
        except StreamingError as e:
            logger.warning("Streaming error", error=e.message, code=e.code)
            yield self._formatter.format_error(e.message, e.code)
        except Exception as e:
            logger.error("Unexpected streaming error", error=str(e), question=request.question[:100])
            yield self._formatter.format_error("Internal server error", "INTERNAL_ERROR")

    async def health_check(self) -> StreamHealthResponse:
        """Check health of streaming service dependencies."""
        try:
            retrieval_health = await self._retrieval.health_check()
            rag_health = await self._rag.health_check()
            ollama_health = await self._ollama.health_check()
            
            retrieval_healthy = (
                getattr(retrieval_health, "vector_store_connected", False) and
                getattr(retrieval_health, "embedding_service_available", False)
            )
            rag_healthy = getattr(rag_health, "status", "") == "healthy"
            ollama_healthy = getattr(ollama_health, "ollama_running", False) and \
                            getattr(ollama_health, "chat_model_available", False)
            
            overall = retrieval_healthy and rag_healthy and ollama_healthy
            
            return StreamHealthResponse(
                status="healthy" if overall else "unhealthy",
                streaming_service_healthy=True,
                retrieval_service_healthy=retrieval_healthy,
                rag_service_healthy=rag_healthy,
                ollama_service_healthy=ollama_healthy,
            )
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return StreamHealthResponse(
                status="unhealthy",
                streaming_service_healthy=False,
                retrieval_service_healthy=False,
                rag_service_healthy=False,
                ollama_service_healthy=False,
                error=str(e),
            )


# Singleton instance
streaming_service = StreamingService()