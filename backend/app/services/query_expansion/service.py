"""Main Query Expansion Service."""

import time
import logging
from typing import List, Optional, Dict, Any

from app.services.query_expansion.expander import query_expander
from app.services.query_expansion.schemas import (
    QueryExpansionConfig,
    QueryExpansionResult,
    QueryExpansionHealthResponse,
)
from app.services.query_expansion.exceptions import (
    QueryExpansionError,
    InvalidQueryError,
)
from app.core.config import get_settings
from app.core.logging import get_logger
from app.monitoring import ai_embedding_time

settings = get_settings()
logger = get_logger(__name__)


class QueryExpansionService:
    """Main query expansion service."""

    def __init__(self, config: Optional[QueryExpansionConfig] = None):
        self._config = config or QueryExpansionConfig()
        self._expander = query_expander
    
    @property
    def config(self) -> QueryExpansionConfig:
        return self._config
    
    @config.setter
    def config(self, value: QueryExpansionConfig) -> None:
        self._config = value
    
    def expand(self, query: str, config: Optional[QueryExpansionConfig] = None) -> QueryExpansionResult:
        """Expand a query using configured expansion methods."""
        if not query or not query.strip():
            raise InvalidQueryError("Query cannot be empty")
        
        effective_config = config or self._config
        
        start_time = time.time()
        try:
            result = query_expander.expand(query, config=effective_config)
            logger.info(
                "Query expansion completed",
                original=query[:100],
                expanded=result.expanded_queries,
                methods=result.expansion_methods,
                time_ms=round(result.expansion_time_ms, 2),
                cache_hit=result.cache_hit,
            )
            
            # Record metrics
            try:
                ai_embedding_time.labels(model="nomic-embed-text", operation="query_expansion").observe(time.time() - start_time)
            except Exception as e:
                logger.warning(f"Failed to record query expansion metrics: {e}")
            
            return result
        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            # Return original query on failure
            return QueryExpansionResult(
                original_query=query,
                normalized_query=query.strip().lower(),
                expanded_queries=[query.strip()],
                expansion_methods=["fallback"],
                expansion_time_ms=0.0,
                cache_hit=False,
            )
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return query_expander.get_cache_stats()
    
    def clear_cache(self) -> None:
        """Clear the expansion cache."""
        query_expander.clear_cache()
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of query expansion service."""
        try:
            cache_stats = self.get_cache_stats()
            return {
                "status": "healthy",
                "cache_size": cache_stats.get("size", 0),
                "cache_hit_rate": cache_stats.get("hit_rate", 0.0),
                "llm_available": False,  # Would check LLM availability
                "fallback_mode": False,
            }
        except Exception as e:
            logger.error(f"Query expansion health check failed: {e}")
            return {
                "status": "unhealthy",
                "cache_size": 0,
                "cache_hit_rate": 0.0,
                "llm_available": False,
                "fallback_mode": True,
                "error": str(e),
            }


# Singleton instance
query_expansion_service = QueryExpansionService()