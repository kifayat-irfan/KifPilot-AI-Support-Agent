from typing import List, Optional
from datetime import datetime
from app.services.vectorstore.models import SearchResult


class RetrievalRanker:
    """Ranks and scores retrieval results using multiple signals."""

    # Weights for different ranking factors
    SIMILARITY_WEIGHT = 0.6
    QUALITY_WEIGHT = 0.2
    FRESHNESS_WEIGHT = 0.2

    @classmethod
    def rank_results(
        cls,
        results: List[SearchResult],
        top_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Rank results using composite scoring.
        
        Ranking factors:
        1. Similarity Score (60%) - from vector search
        2. Chunk Quality (20%) - based on token count, section presence
        3. Document Freshness (20%) - based on created_at
        
        Args:
            results: Raw search results from vector store
            top_k: Optional limit on number of results
            
        Returns:
            Ranked and scored results
        """
        if not results:
            return []

        # Calculate quality and freshness scores
        scored_results = []
        for result in results:
            quality_score = cls._calculate_quality_score(result)
            freshness_score = cls._calculate_freshness_score(result)
            
            # Composite score
            composite_score = (
                cls.SIMILARITY_WEIGHT * result.score +
                cls.QUALITY_WEIGHT * quality_score +
                cls.FRESHNESS_WEIGHT * freshness_score
            )
            
            # Store composite score in metadata for reference
            result.metadata = result.metadata or {}
            result.metadata["composite_score"] = composite_score
            result.metadata["quality_score"] = quality_score
            result.metadata["freshness_score"] = freshness_score
            
            scored_results.append(result)

        # Sort by composite score descending
        scored_results.sort(key=lambda r: r.metadata.get("composite_score", 0), reverse=True)

        # Apply top_k limit
        if top_k:
            scored_results = scored_results[:top_k]

        # Normalize scores to 0-1 range
        cls._normalize_scores(scored_results)

        return scored_results

    @classmethod
    def _calculate_quality_score(cls, result: SearchResult) -> float:
        """Calculate chunk quality score (0-1)."""
        metadata = result.metadata or {}
        
        score = 0.5  # Base score
        
        # Token count factor (prefer substantial chunks)
        token_count = metadata.get("token_count", 0)
        if token_count > 200:
            score += 0.2
        elif token_count > 100:
            score += 0.1
        elif token_count < 50:
            score -= 0.1
        
        # Section/heading presence (structured content is better)
        if metadata.get("section") or metadata.get("heading"):
            score += 0.15
        
        # Page number presence
        if metadata.get("page"):
            score += 0.05
        
        return max(0.0, min(1.0, score))

    @classmethod
    def _calculate_freshness_score(cls, result: SearchResult) -> float:
        """Calculate document freshness score (0-1)."""
        metadata = result.metadata or {}
        
        created_at_str = metadata.get("created_at")
        if not created_at_str:
            return 0.5  # Neutral if no date
        
        try:
            # Parse datetime - handle both string and datetime objects
            if isinstance(created_at_str, str):
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            else:
                created_at = created_at_str
            
            now = datetime.utcnow()
            age_days = (now - created_at).days
            
            # Exponential decay: newer documents get higher scores
            # Half-life of 365 days
            if age_days <= 0:
                return 1.0
            elif age_days <= 30:
                return 0.9
            elif age_days <= 90:
                return 0.7
            elif age_days <= 180:
                return 0.5
            elif age_days <= 365:
                return 0.3
            else:
                return 0.1
                
        except Exception:
            return 0.5  # Neutral on parse error

    @classmethod
    def _normalize_scores(cls, results: List[SearchResult]) -> None:
        """Normalize composite scores to 0-1 range."""
        if not results:
            return
        
        scores = [r.metadata.get("composite_score", 0) for r in results]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            # All scores equal, set to 1.0
            for r in results:
                r.metadata["composite_score"] = 1.0
            return
        
        # Min-max normalization
        for r in results:
            raw = r.metadata.get("composite_score", 0)
            normalized = (raw - min_score) / (max_score - min_score)
            r.metadata["composite_score"] = round(normalized, 4)