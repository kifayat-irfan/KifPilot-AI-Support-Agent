import time
from typing import List, Optional, Dict, Any
from uuid import UUID

from app.services.vectorstore import vector_store_service
from app.services.vectorstore.models import SimilaritySearchRequest, SearchResult
from app.services.llm import ollama_service as ollama_service_instance
from app.services.llm.models import EmbeddingRequest
from app.services.retrieval.schemas import RetrievalFilters
from app.services.retrieval.filters import FilterBuilder
from app.services.retrieval.exceptions import (
    RetrievalError,
    EmbeddingGenerationError,
    VectorSearchError,
    InvalidFiltersError,
    InvalidUUIDError,
)


class RetrievalSearcher:
    """Handles semantic vector search using existing services."""

    def __init__(
        self,
        vector_store=None,
        ollama_service=None,
    ):
        self._vector_store = vector_store or vector_store_service
        self._ollama_service = ollama_service or ollama_service_instance

    async def search(
        self,
        query: str,
        top_k: int = 10,
        minimum_score: float = 0.0,
        filters: Optional[RetrievalFilters] = None,
        organization_id: Optional[str] = None,
    ) -> List[SearchResult]:
        """
        Perform semantic search with optional filters.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            minimum_score: Minimum similarity score threshold (0-1)
            filters: Optional metadata filters
            organization_id: Optional organization ID for multi-tenant isolation
            
        Returns:
            List of SearchResult objects
        """
        start_time = time.time()

        # Generate embedding for query
        query_embedding = await self._generate_query_embedding(query)

        # Build where clause from filters
        where_clause = None
        if filters:
            try:
                where_clause = FilterBuilder.build_where_clause(filters)
            except Exception as e:
                raise InvalidFiltersError(f"Failed to build filters: {str(e)}")

        # Add organization_id filter if provided
        if organization_id:
            if where_clause is None:
                where_clause = {}
            where_clause["organization_id"] = organization_id

        # Perform vector search
        try:
            search_request = SimilaritySearchRequest(
                organization_id=organization_id,
                query_embedding=query_embedding,
                n_results=top_k,
                where=where_clause,
            )
            
            response = await self._vector_store.similarity_search(search_request)
            results = response.results

        except Exception as e:
            raise VectorSearchError(f"Vector search failed: {str(e)}")

        # Filter by minimum score
        filtered_results = [
            r for r in results 
            if r.score >= minimum_score
        ]

        search_time_ms = (time.time() - start_time) * 1000

        return filtered_results, search_time_ms

    async def _generate_query_embedding(self, query: str) -> List[float]:
        """Generate embedding for search query."""
        try:
            request = EmbeddingRequest(input=[query])
            response = await self._ollama_service.generate_embeddings(request)
            return response.embeddings[0]
        except Exception as e:
            raise EmbeddingGenerationError(f"Failed to generate query embedding: {str(e)}")

    async def health_check(self, organization_id: Optional[str] = None) -> Dict[str, Any]:
        """Check health of retrieval dependencies."""
        vector_health = await self._vector_store.health_check(organization_id)
        
        try:
            ollama_health = await self._ollama_service.health_check()
            embedding_available = ollama_health.embed_model_available
        except Exception:
            embedding_available = False

        return {
            "vector_store_connected": vector_health.chromadb_running and vector_health.collection_exists,
            "embedding_service_available": embedding_available,
            "vector_store_status": vector_health.status,
        }