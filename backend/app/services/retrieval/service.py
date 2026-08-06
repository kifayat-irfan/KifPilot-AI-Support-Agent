"""Main Context Compression Service integrating with the retrieval pipeline."""

import time
import logging
from typing import List, Optional, Dict, Any, Tuple

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
    NoResultsError,
    ContextBuildError,
    InvalidTopKError,
)
from app.services.query_expansion import query_expander
from app.services.query_expansion.schemas import QueryExpansionConfig
from app.services.query_expansion.exceptions import QueryExpansionError
from app.services.hybrid_search import hybrid_search_service
from app.services.hybrid_search.schemas import HybridSearchRequest, HybridSearchResponse
from app.services.reranker import reranker_service
from app.core.config import get_settings
from app.core.logging import get_logger
from app.monitoring import (
    record_retrieval_metrics,
    record_ai_generation,
    ai_embedding_time,
    ai_hybrid_search_time,
    ai_rrf_time,
    ai_reranker_time,
    ai_context_compression_time,
)

settings = get_settings()
logger = get_logger(__name__)


class RetrievalService:
    """Main retrieval service orchestrating search, ranking, and context building."""

    def __init__(
        self,
        searcher: Optional[RetrievalSearcher] = None,
        ranker: Optional[RetrievalRanker] = None,
        context_builder: Optional[ContextBuilder] = None,
        reranker: Optional["RerankerService"] = None,
    ):
        self._searcher = searcher or RetrievalSearcher()
        self._ranker = ranker or RetrievalRanker()
        self._context_builder = context_builder or ContextBuilder()
        self._reranker = reranker_service
        self._default_min_score = getattr(settings, 'RETRIEVAL_MIN_SCORE', 0.3)
        self._default_max_context = getattr(settings, 'RETRIEVAL_MAX_CONTEXT', 8000)

    async def search(
        self, 
        request: RetrievalSearchRequest,
        organization_id: Optional[str] = None,
    ) -> RetrievalSearchResponse:
        """
        Perform semantic search with ranking.
        
        Args:
            request: Search request with query, filters, and parameters
            organization_id: Optional organization ID for multi-tenant isolation
             
        Returns:
            Ranked search results
        """
        start_time = time.time()

        # Validate query
        if not request.query or not request.query.strip():
            raise EmptyQueryError()

        # Validate top_k
        if request.top_k < 1 or request.top_k > 20:
            raise InvalidTopKError(request.top_k)

        logger.info(
            "Retrieval search started",
            query=request.query[:100],
            top_k=request.top_k,
            minimum_score=request.minimum_score,
            filters=request.filters.dict() if request.filters else None,
            organization_id=organization_id,
        )

        # Perform vector search
        raw_results, search_time_ms = await self._searcher.search(
            query=request.query.strip(),
            top_k=request.top_k,
            minimum_score=request.minimum_score,
            filters=request.filters,
            organization_id=organization_id,
        )

        if not raw_results:
            logger.info("No results found", query=request.query[:100], organization_id=organization_id)
            return RetrievalSearchResponse(
                search_time_ms=search_time_ms,
                total_results=0,
                results=[],
            )

        # Rank results
        ranked_results = self._ranker.rank_results(raw_results, top_k=request.top_k)

        # Convert to response format
        results = []
        scores = []
        for result in ranked_results:
            metadata = result.metadata or {}
            similarity_score = round(metadata.get("composite_score", result.score), 4)
            scores.append(similarity_score)
            retrieval_result = RetrievalResult(
                document_id=metadata.get("document_id", ""),
                document_name=metadata.get("document_name", "Unknown"),
                chunk_id=metadata.get("chunk_id", result.id),
                chunk_index=metadata.get("chunk_index", 0),
                page=metadata.get("page"),
                section=metadata.get("section"),
                text=result.document,
                similarity_score=similarity_score,
                metadata={
                    "similarity_score": round(result.score, 4),
                    "quality_score": round(metadata.get("quality_score", 0), 4),
                    "freshness_score": round(metadata.get("freshness_score", 0), 4),
                    "composite_score": round(metadata.get("composite_score", 0), 4),
                    "file_type": metadata.get("file_type"),
                    "language": metadata.get("language"),
                    "category": metadata.get("category"),
                    "company": metadata.get("company"),
                    "created_at": metadata.get("created_at"),
                },
            )
            results.append(retrieval_result)

        total_time_ms = (time.time() - start_time) * 1000

        # Record retrieval metrics
        try:
            record_retrieval_metrics(
                method="vector",
                collection="default",
                duration_seconds=search_time_ms / 1000,
                result_count=len(results),
                scores=scores,
            )
        except Exception as e:
            logger.warning(f"Failed to record retrieval metrics: {e}")

        logger.info(
            "Retrieval search completed",
            query=request.query[:100],
            results_count=len(results),
            search_time_ms=round(search_time_ms, 2),
            total_time_ms=round(total_time_ms, 2),
            organization_id=organization_id,
        )

        return RetrievalSearchResponse(
            search_time_ms=round(total_time_ms, 2),
            total_results=len(results),
            results=results,
        )

    async def build_context(
        self, 
        request: RetrievalContextRequest,
        organization_id: Optional[str] = None,
    ) -> RetrievalContextResponse:
        """
        Build context for RAG from search results.
        
        Pipeline:
        1. Query Expansion (expand user query)
        2. Hybrid Search (Vector + BM25 + RRF) -> Top candidates
        3. Cross-Encoder Reranking (if enabled) -> Top results
        5. Context Compression (deduplicate, merge, remove low-value, token budget)
        6. Context Building
        
        Args:
            request: Context build request
            organization_id: Optional organization ID for multi-tenant isolation
             
        Returns:
            Built context with source attribution
        """
        start_time = time.time()

        # Validate query
        if not request.query or not request.query.strip():
            raise EmptyQueryError()

        # Validate top_k
        if request.top_k < 1 or request.top_k > 20:
            raise InvalidTopKError(request.top_k)

        logger.info(
            "Context building started",
            query=request.query[:100],
            top_k=request.top_k,
            max_context_chars=request.max_context_chars,
            organization_id=organization_id,
        )

        # Step 1: Query Expansion
        expansion_start = time.time()
        expanded_queries = [request.query.strip()]
        expansion_used = False
        
        try:
            from app.services.query_expansion import query_expander
            from app.services.query_expansion.schemas import QueryExpansionConfig
            
            # Create config from settings
            expansion_config = QueryExpansionConfig(
                enabled=getattr(settings, 'QUERY_EXPANSION_ENABLED', True),
                max_expanded_queries=getattr(settings, 'QUERY_EXPANSION_MAX_QUERIES', 5),
                cache_enabled=getattr(settings, 'QUERY_EXPANSION_CACHE_ENABLED', True),
                cache_ttl_seconds=getattr(settings, 'QUERY_EXPANSION_CACHE_TTL_SECONDS', 3600),
                use_llm_expansion=getattr(settings, 'QUERY_EXPANSION_USE_LLM', False),
                llm_timeout_seconds=getattr(settings, 'QUERY_EXPANSION_LLM_TIMEOUT_SECONDS', 3.0),
            )
            
            expansion_result = query_expander.expand(request.query.strip(), config=expansion_config)
            if expansion_result and expansion_result.expanded_queries:
                expanded_queries = expansion_result.expanded_queries
                expansion_used = True
                logger.info(
                    "Query expanded",
                    original=request.query[:100],
                    expanded=expansion_result.expanded_queries,
                    methods=expansion_result.expansion_methods,
                )
        except Exception as e:
            logger.warning(f"Query expansion failed, using original query: {e}")
        
        expansion_time_ms = (time.time() - expansion_start) * 1000
        
        # Record query expansion metrics
        try:
            if expansion_used:
                ai_embedding_time.labels(model="nomic-embed-text", operation="expand").observe(expansion_time_ms / 1000)
        except Exception as e:
            logger.warning(f"Failed to record expansion metrics: {e}")
        
        # Step 2: Hybrid Search with expanded queries
        hybrid_start = time.time()
        all_results = []
        seen_chunk_ids = set()
        
        for i, eq in enumerate(expanded_queries):
            hybrid_request = HybridSearchRequest(
                query=eq,
                top_k=max(20, request.top_k * 2),  # Get more candidates for compression
                minimum_score=request.minimum_score,
                rrf_constant=60,
                vector_weight=1.0,
                bm25_weight=1.0,
                filters=request.filters,
                include_vector_scores=True,
                include_bm25_scores=True,
            )
            
            hybrid_response = await hybrid_search_service.search(
                request=hybrid_request,
                organization_id=organization_id,
            )
            
            # Deduplicate by chunk_id
            for result in hybrid_response.results:
                if result.chunk_id not in seen_chunk_ids:
                    seen_chunk_ids.add(result.chunk_id)
                    all_results.append(result)
        
        hybrid_time_ms = (time.time() - hybrid_start) * 1000
        
        # Record hybrid search metrics
        try:
            ai_hybrid_search_time.labels(query_type="expanded" if expansion_used else "single").observe(hybrid_time_ms / 1000)
            ai_rrf_time.labels(fusion_type="rrf").observe(hybrid_time_ms / 1000)  # RRF is part of hybrid search
        except Exception as e:
            logger.warning(f"Failed to record hybrid search metrics: {e}")
        
        if not all_results:
            logger.info("Hybrid search returned no results")
            raise NoResultsError()
        
        # Step 3: Reranking (if enabled)
        reranker_start = time.time()
        reranked_results = all_results
        
        try:
            from app.services.reranker import reranker_service
            reranked = await reranker_service.rerank_context(
                query=request.query.strip(),
                candidates=all_results,
                top_k=request.top_k,
            )
            if reranked:
                reranked_results = reranked
        except Exception as e:
            logger.warning(f"Reranking failed: {e}, using hybrid scores")
        
        reranker_time_ms = (time.time() - reranker_start) * 1000
        
        # Record reranker metrics
        try:
            if reranked_results is not all_results:
                ai_reranker_time.labels(model="cross-encoder", candidate_count=str(len(all_results))).observe(reranker_time_ms / 1000)
        except Exception as e:
            logger.warning(f"Failed to record reranker metrics: {e}")
        
        # Step 4: Take top_k
        final_results = reranked_results[:request.top_k]
        
        # Step 5: Context Compression (NEW)
        compression_start = time.time()
        compressed_chunks = final_results
        compression_used = False
        compression_stats = {}
        
        try:
            from app.services.context_compression.compressor import ChunkCompressor
            from app.services.context_compression.selector import ChunkSelector
            from app.services.context_compression.schemas import ContextCompressionConfig
            
            # Create compression config from settings
            compression_config = ContextCompressionConfig(
                enabled=getattr(settings, 'CONTEXT_COMPRESSION_ENABLED', True),
                deduplicate_enabled=True,
                deduplication_threshold=0.95,
                merge_enabled=True,
                merge_same_document=True,
                merge_max_distance=2,
                remove_low_value=True,
                remove_empty_lines=True,
                remove_repeated_headers=True,
                remove_boilerplate=True,
                preserve_tables=True,
                preserve_lists=True,
                preserve_code_blocks=True,
                preserve_warnings=True,
                preserve_notes=True,
                preserve_headings=True,
                preserve_page_numbers=True,
                preserve_document_order=True,
                max_tokens=getattr(settings, 'CONTEXT_COMPRESSION_MAX_TOKENS', 8000),
                max_documents=getattr(settings, 'CONTEXT_COMPRESSION_MAX_DOCUMENTS', 20),
                max_chunks=getattr(settings, 'CONTEXT_COMPRESSION_MAX_CHUNKS', 50),
            )
            
            # Convert to format expected by compressor
            from app.services.reranker.schemas import RerankedResult
            
            candidates = []
            for r in final_results:
                candidate = RerankedResult(
                    chunk_id=r.chunk_id,
                    document_id=r.document_id,
                    document_name=r.document_name,
                    chunk_index=r.chunk_index,
                    page=r.page,
                    section=r.section,
                    text=r.text,
                    hybrid_score=r.similarity_score,
                    reranker_score=r.metadata.get("reranker_score", r.similarity_score) if r.metadata else r.similarity_score,
                    final_score=r.metadata.get("final_score", r.similarity_score) if r.metadata else r.similarity_score,
                    vector_score=r.metadata.get("vector_score") if r.metadata else None,
                    bm25_score=r.metadata.get("bm25_score") if r.metadata else None,
                    metadata=r.metadata or {},
                )
                candidates.append(candidate)
            
            # Use ChunkCompressor for deduplication and merging
            compressor_config = {
                "remove_empty_lines": compression_config.remove_empty_lines,
                "remove_repeated_headers": compression_config.remove_repeated_headers,
                "remove_boilerplate": compression_config.remove_boilerplate,
                "preserve_tables": compression_config.preserve_tables,
                "preserve_lists": compression_config.preserve_lists,
                "preserve_code_blocks": compression_config.preserve_code_blocks,
                "preserve_warnings": compression_config.preserve_warnings,
                "preserve_notes": compression_config.preserve_notes,
                "preserve_headings": compression_config.preserve_headings,
                "preserve_page_numbers": compression_config.preserve_page_numbers,
            }
            compressor = ChunkCompressor(compressor_config)
            
            # Convert candidates to dict format for compressor
            chunks_dict = []
            for c in candidates:
                chunks_dict.append({
                    "chunk_id": c.chunk_id,
                    "document_id": c.document_id,
                    "document_name": c.document_name,
                    "chunk_index": c.chunk_index,
                    "page": c.page,
                    "section": c.section,
                    "text": c.text,
                    "score": c.final_score,
                    "similarity_score": c.similarity_score,
                    "final_score": c.final_score,
                    "hybrid_score": c.hybrid_score,
                    "vector_score": c.vector_score,
                    "bm25_score": c.bm25_score,
                    "metadata": c.metadata,
                })
            
            # Compress the chunks
            compression_result = compressor.compress(
                chunks=chunks_dict,
                token_budget=request.max_context_chars // 4,  # Convert chars to tokens (rough estimate)
            )
            
            # Use ChunkSelector for token budget management
            selector = ChunkSelector({
                "max_tokens": compression_config.max_tokens,
                "max_documents": compression_config.max_documents,
                "max_chunks": compression_config.max_chunks,
                "preserve_document_order": compression_config.preserve_document_order,
                "preserve_page_numbers": compression_config.preserve_page_numbers,
            })
            
            selection_result = selector.select_chunks(
                chunks=compression_result.chunks,
                token_budget=request.max_context_chars // 4,
            )
            
            if selection_result.selected_chunks:
                compressed_chunks = selection_result.selected_chunks
                compression_used = True
                compression_stats = {
                    "original_chunks": len(candidates),
                    "compressed_chunks": len(selection_result.selected_chunks),
                    "original_tokens": int(sum(len(c.get("text", "") or c.get("content", "")) for c in chunks_dict) / 4),
                    "compressed_tokens": selection_result.total_tokens,
                    "compression_ratio": selection_result.total_tokens / max(1, int(sum(len(c.get("text", "") or c.get("content", "")) for c in chunks_dict) / 4)),
                    "tokens_saved": int(sum(len(c.get("text", "") or c.get("content", "")) for c in chunks_dict) / 4) - selection_result.total_tokens,
                    "deduplicated_count": compression_result.low_value_removed_count,
                    "merged_count": compression_result.merged_count,
                    "low_value_removed_count": compression_result.low_value_removed_count,
                }
                logger.info(
                    "Context compression applied",
                    original=compression_result.original_chunks,
                    compressed=compression_result.compressed_chunks,
                    ratio=round(compression_result.compression_ratio, 3),
                    tokens_saved=compression_result.tokens_saved,
                )
        except Exception as e:
            logger.warning(f"Context compression failed: {e}, using original chunks")
        
        compression_time_ms = (time.time() - compression_start) * 1000
        
        # Record context compression metrics
        try:
            if compression_used:
                ai_context_compression_time.labels(
                    strategy="full",
                    chunk_count=str(compression_stats.get("original_chunks", 0))
                ).observe(compression_time_ms / 1000)
        except Exception as e:
            logger.warning(f"Failed to record compression metrics: {e}")
        
        # Step 6: Convert to SearchResult format for context builder
        from app.services.vectorstore.models import SearchResult
        raw_results = []
        
        # Use compressed chunks if available, otherwise use final_results
        source_chunks = compressed_chunks if compression_used else final_results
        
        for r in source_chunks:
            # Handle both RerankedResult (from compression) and RetrievalResult (original)
            chunk_id = getattr(r, 'chunk_id', getattr(r, 'id', ''))
            document_id = getattr(r, 'document_id', '')
            document_name = getattr(r, 'document_name', 'Unknown')
            chunk_index = getattr(r, 'chunk_index', 0)
            page = getattr(r, 'page', None)
            section = getattr(r, 'section', None)
            text = getattr(r, 'text', '')
            similarity_score = getattr(r, 'similarity_score', getattr(r, 'final_score', getattr(r, 'hybrid_score', 0.0)))
            
            raw_results.append(SearchResult(
                id=chunk_id,
                document=text,
                metadata={
                    "document_id": document_id,
                    "document_name": document_name,
                    "chunk_id": chunk_id,
                    "chunk_index": chunk_index,
                    "page": page,
                    "section": section,
                    "similarity_score": similarity_score,
                    **getattr(r, 'metadata', {}),
                },
                distance=1.0 - similarity_score,
                score=similarity_score,
            ))

        # Step 6: Build context
        try:
            context_text, used_results, citation_map = self._context_builder.build_context_with_citations(
                raw_results,
                request.query.strip(),
            )
        except Exception as e:
            raise ContextBuildError(f"Failed to build context: {str(e)}")

        total_time_ms = (time.time() - start_time) * 1000

        # Convert used results to response format
        sources = []
        for r in used_results:
            metadata = r.metadata or {}
            sources.append(RetrievalResult(
                document_id=metadata.get("document_id", ""),
                document_name=metadata.get("document_name", "Unknown"),
                chunk_id=metadata.get("chunk_id", r.id),
                chunk_index=metadata.get("chunk_index", 0),
                page=metadata.get("page"),
                section=metadata.get("section"),
                text=r.document,
                similarity_score=round(metadata.get("composite_score", r.score), 4),
                metadata={
                    "similarity_score": round(r.score, 4),
                    "quality_score": round(metadata.get("quality_score", 0), 4),
                    "freshness_score": round(metadata.get("freshness_score", 0), 4),
                    "composite_score": round(metadata.get("composite_score", 0), 4),
                    "file_type": metadata.get("file_type"),
                    "language": metadata.get("language"),
                    "category": metadata.get("category"),
                    "company": metadata.get("company"),
                    "created_at": metadata.get("created_at"),
                },
            ))

        logger.info(
            "Context building completed",
            query=request.query[:100],
            chunks_used=len(sources),
            context_chars=len(context_text),
            total_time_ms=round(total_time_ms, 2),
            expansion_time_ms=round(expansion_time_ms, 2),
            hybrid_time_ms=round(hybrid_time_ms, 2),
            reranker_time_ms=round(reranker_time_ms, 2),
            compression_time_ms=round(compression_time_ms, 2),
            expansion_used=expansion_used,
            compression_used=compression_used,
            compression_stats=compression_stats,
            organization_id=organization_id,
        )

        return RetrievalContextResponse(
            context=context_text,
            search_time_ms=round(total_time_ms, 2),
            total_chunks=len(sources),
            total_chars=len(context_text),
            sources=sources,
        )

    async def health_check(self, organization_id: Optional[str] = None) -> HealthCheckResponse:
        """Check health of retrieval system."""
        try:
            deps = await self._searcher.health_check(organization_id)
            
            overall_healthy = (
                deps.get("vector_store_connected", False) and 
                deps.get("embedding_service_available", False)
            )

            return HealthCheckResponse(
                status="healthy" if overall_healthy else "unhealthy",
                vector_store_connected=deps.get("vector_store_connected", False),
                embedding_service_available=deps.get("embedding_service_available", False),
            )
        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return HealthCheckResponse(
                status="unhealthy",
                vector_store_connected=False,
                embedding_service_available=False,
                error=str(e),
            )


# Singleton instance
retrieval_service = RetrievalService()