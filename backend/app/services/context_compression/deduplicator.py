"""Deduplication logic for context compression."""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DeduplicationResult:
    """Result of deduplication process."""
    unique_chunks: List[Dict[str, Any]]
    duplicate_count: int
    removed_chunk_ids: List[str]


class ChunkDeduplicator:
    """Handles deduplication of chunks based on content similarity."""
    
    def __init__(
        self,
        threshold: float = 0.95,
        method: str = "jaccard",
    ):
        """
        Initialize the deduplicator.
        
        Args:
            threshold: Similarity threshold (0-1), chunks above this are considered duplicates
            method: Similarity calculation method ("jaccard", "cosine", "levenshtein")
        """
        self.threshold = threshold
        self.method = method
    
    def deduplicate(
        self,
        chunks: List[Dict[str, Any]],
        similarity_key: str = "text",
    ) -> DeduplicationResult:
        """
        Remove duplicate chunks based on content similarity.
        
        Args:
            chunks: List of chunk dictionaries
            similarity_key: Key to use for similarity comparison
            
        Returns:
            DeduplicationResult with unique chunks and statistics
        """
        if not chunks:
            return DeduplicationResult(
                unique_chunks=[],
                duplicate_count=0,
                removed_chunk_ids=[]
            )
        
        unique_chunks = []
        removed_ids = []
        seen_signatures = {}
        
        for chunk in chunks:
            chunk_id = chunk.get("chunk_id") or chunk.get("id") or str(id(chunk))
            text = chunk.get(similarity_key, "")
            
            if not text:
                unique_chunks.append(chunk)
                continue
            
            # Generate signature for fast exact duplicate detection
            signature = self._generate_signature(text)
            
            if signature in seen_signatures:
                # Exact duplicate found
                existing = seen_signatures[signature]
                existing_score = existing.get("score", 0)
                current_score = chunk.get("score", 0) or chunk.get("similarity_score", 0) or chunk.get("final_score", 0) or chunk.get("rrf_score", 0) or 0
                
                if current_score > existing_score:
                    # Replace with higher scoring chunk
                    unique_chunks = [c for c in unique_chunks if c.get("chunk_id") != seen_signatures[signature]]
                    unique_chunks.append(chunk)
                    seen_signatures[signature] = chunk
                    removed_ids.append(existing.get("chunk_id", "unknown"))
                else:
                    # Keep existing, discard current
                    removed_ids.append(chunk_id)
            else:
                # Not a duplicate
                seen_signatures[signature] = chunk
                unique_chunks.append(chunk)
        
        logger.info(
            "Deduplication completed",
            original_count=len(chunks),
            unique_count=len(unique_chunks),
            duplicate_count=len(removed_ids),
        )
        
        return DeduplicationResult(
            unique_chunks=unique_chunks,
            duplicate_count=len(removed_ids),
            removed_chunk_ids=removed_ids,
        )
    
    def _generate_signature(self, text: str) -> str:
        """Generate a signature for exact duplicate detection."""
        import hashlib
        # Normalize text for signature
        normalized = " ".join(text.lower().split())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts."""
        if self.method == "jaccard":
            return self._jaccard_similarity(text1, text2)
        elif self.method == "cosine":
            return self._cosine_similarity(text1, text2)
        elif self.method == "levenshtein":
            return self._levenshtein_similarity(text1, text2)
        return 0.0
    
    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        
        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0
        
        intersection = set1 & set2
        union = set1 | set2
        return len(intersection) / len(union)
    
    def _cosine_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity between two texts."""
        from collections import Counter
        import math
        
        vec1 = Counter(text1.lower().split())
        vec2 = Counter(text2.lower().split())
        
        if not vec1 and not vec2:
            return 1.0
        if not vec1 or not vec2:
            return 0.0
        
        # Dot product
        dot_product = sum(vec1.get(k, 0) * vec2.get(k, 0) for k in set(vec1) | set(vec2))
        
        # Magnitudes
        mag1 = math.sqrt(sum(v * v for v in vec1.values()))
        mag2 = math.sqrt(sum(v * v for v in vec2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def _levenshtein_similarity(self, text1: str, text2: str) -> float:
        """Calculate Levenshtein similarity between two texts."""
        # Simplified - only for short texts
        if len(text1) > 1000 or len(text2) > 1000:
            return self._jaccard_similarity(text1, text2)
        
        # Levenshtein distance
        if len(text1) < len(text2):
            text1, text2 = text2, text1
        
        if len(text2) == 0:
            return 0.0
        
        previous_row = list(range(len(text2) + 1))
        for i, c1 in enumerate(text1):
            current_row = [i + 1]
            for j, c2 in enumerate(text2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        distance = previous_row[-1]
        max_len = max(len(text1), len(text2))
        if max_len == 0:
            return 1.0
        return 1.0 - (distance / max_len)