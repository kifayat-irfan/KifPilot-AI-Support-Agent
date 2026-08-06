"""Rank fusion algorithms for hybrid search."""

import logging
import math
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RankedResult:
    """A result with its rank and score from a single search method."""
    chunk_id: str
    document_id: str
    document_name: str
    text: str
    metadata: Dict[str, Any]
    rank: int
    score: float
    score_type: str  # 'vector' or 'bm25'


def reciprocal_rank_fusion(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    k: int = 60,
    vector_weight: float = 1.0,
    bm25_weight: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Fuse vector and BM25 search results using Reciprocal Rank Fusion (RRF).
    
    RRF formula: score = sum(weight_i / (k + rank_i)) for each system i
    
    Args:
        vector_results: List of vector search results with chunk_id, rank, score
        bm25_results: List of BM25 search results with chunk_id, rank, score
        k: RRF constant (typically 60)
        vector_weight: Weight for vector search results
        bm25_weight: Weight for BM25 search results
        
    Returns:
        Fused results sorted by RRF score descending
    """
    # Build rank maps
    vector_ranks = {}
    for i, result in enumerate(vector_results):
        chunk_id = result.get("chunk_id") or result.get("id")
        if chunk_id:
            vector_ranks[chunk_id] = i + 1  # 1-based rank
    
    bm25_ranks = {}
    for i, result in enumerate(bm25_results):
        chunk_id = result.get("chunk_id") or result.get("id")
        if chunk_id:
            bm25_ranks[chunk_id] = i + 1  # 1-based rank
    
    # Get all unique chunk IDs
    all_chunk_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())
    
    # Calculate RRF scores
    fused_results = []
    for chunk_id in all_chunk_ids:
        rrf_score = 0.0
        
        # Vector contribution
        if chunk_id in vector_ranks:
            rank = vector_ranks[chunk_id]
            rrf_score += vector_weight / (k + rank)
        
        # BM25 contribution
        if chunk_id in bm25_ranks:
            rank = bm25_ranks[chunk_id]
            rrf_score += bm25_weight / (k + rank)
        
        # Get the full result data from either source (prefer vector for metadata)
        source_result = None
        for r in vector_results:
            if (r.get("chunk_id") or r.get("id")) == chunk_id:
                source_result = r
                break
        if not source_result:
            for r in bm25_results:
                if (r.get("chunk_id") or r.get("id")) == chunk_id:
                    source_result = r
                    break
        
        if source_result:
            fused_results.append({
                "chunk_id": chunk_id,
                "document_id": source_result.get("document_id", ""),
                "document_name": source_result.get("document_name", "Unknown"),
                "chunk_id": chunk_id,
                "chunk_index": source_result.get("chunk_index", 0),
                "page": source_result.get("page"),
                "section": source_result.get("section"),
                "text": source_result.get("text") or source_result.get("document", ""),
                "rrf_score": rrf_score,
                "vector_rank": vector_ranks.get(chunk_id),
                "bm25_rank": bm25_ranks.get(chunk_id),
                "vector_score": source_result.get("score"),
                "bm25_score": source_result.get("bm25_score") or source_result.get("score"),
                "metadata": source_result.get("metadata", {}),
            })
    
    # Sort by RRF score descending
    fused_results.sort(key=lambda x: x["rrf_score"], reverse=True)
    
    # Normalize RRF scores to 0-1 range
    if fused_results:
        max_score = max(r["rrf_score"] for r in fused_results)
        min_score = min(r["rrf_score"] for r in fused_results)
        
        if max_score > min_score:
            for r in fused_results:
                r["rrf_score"] = (r["rrf_score"] - min_score) / (max_score - min_score)
        else:
            for r in fused_results:
                r["rrf_score"] = 1.0
    
    return fused_results


def weighted_score_fusion(
    vector_results: List[Dict[str, Any]],
    bm25_results: List[Dict[str, Any]],
    vector_weight: float = 0.7,
    bm25_weight: float = 0.3,
) -> List[Dict[str, Any]]:
    """
    Fuse results using weighted score combination.
    
    Args:
        vector_results: Vector search results
        bm25_results: BM25 search results
        vector_weight: Weight for vector scores
        bm25_weight: Weight for BM25 scores
        
    Returns:
        Fused results sorted by weighted score
    """
    # Build score maps
    vector_scores = {}
    for r in vector_results:
        chunk_id = r.get("chunk_id") or r.get("id")
        if chunk_id:
            vector_scores[chunk_id] = r.get("score", 0.0)
    
    bm25_scores = {}
    for r in bm25_results:
        chunk_id = r.get("chunk_id") or r.get("id")
        if chunk_id:
            bm25_scores[chunk_id] = r.get("score", 0.0) or r.get("bm25_score", 0.0)
    
    # Normalize scores to 0-1 range
    if vector_scores:
        max_v = max(vector_scores.values()) if vector_scores else 1.0
        min_v = min(vector_scores.values()) if vector_scores else 0.0
        if max_v > min_v:
            for cid in vector_scores:
                vector_scores[cid] = (vector_scores[cid] - min_v) / (max_v - min_v)
        else:
            for cid in vector_scores:
                vector_scores[cid] = 1.0
    
    if bm25_scores:
        max_b = max(bm25_scores.values()) if bm25_scores else 1.0
        min_b = min(bm25_scores.values()) if bm25_scores else 0.0
        if max_b > min_b:
            for cid in bm25_scores:
                bm25_scores[cid] = (bm25_scores[cid] - min_b) / (max_b - min_b)
        else:
            for cid in bm25_scores:
                bm25_scores[cid] = 1.0
    
    # Combine scores
    all_chunk_ids = set(vector_scores.keys()) | set(bm25_scores.keys())
    fused = []
    
    for chunk_id in all_chunk_ids:
        v_score = vector_scores.get(chunk_id, 0.0)
        b_score = bm25_scores.get(chunk_id, 0.0)
        
        combined_score = (vector_weight * v_score) + (bm25_weight * b_score)
        
        # Get source result
        source = None
        for r in vector_results:
            if (r.get("chunk_id") or r.get("id")) == chunk_id:
                source = r
                break
        if not source:
            for r in bm25_results:
                if (r.get("chunk_id") or r.get("id")) == chunk_id:
                    source = r
                    break
        
        if source:
            fused.append({
                "chunk_id": chunk_id,
                "document_id": source.get("document_id", ""),
                "document_name": source.get("document_name", "Unknown"),
                "text": source.get("text") or source.get("document", ""),
                "fused_score": combined_score,
                "vector_score": v_score,
                "bm25_score": b_score,
                "metadata": source.get("metadata", {}),
            })
    
    fused.sort(key=lambda x: x["fused_score"], reverse=True)
    return fused


def deduplicate_results(
    results: List[Dict[str, Any]],
    key: str = "chunk_id",
) -> List[Dict[str, Any]]:
    """
    Remove duplicate results based on a key.
    
    Args:
        results: List of results
        key: Field to use for deduplication
        
    Returns:
        Deduplicated results
    """
    seen = set()
    deduplicated = []
    
    for result in results:
        result_key = result.get(key)
        if result_key and result_key not in seen:
            seen.add(result_key)
            deduplicated.append(result)
    
    return deduplicated


def normalize_scores(
    results: List[Dict[str, Any]],
    score_field: str = "score",
    min_val: float = 0.0,
    max_val: float = 1.0,
) -> List[Dict[str, Any]]:
    """
    Normalize scores in results to a specified range.
    
    Args:
        results: List of results with scores
        score_field: Field name containing the score
        min_val: Minimum output value
        max_val: Maximum output value
        
    Returns:
        Results with normalized scores
    """
    if not results:
        return results
    
    scores = [r.get(score_field, 0.0) for r in results]
    min_score = min(scores)
    max_score = max(scores)
    
    if max_score == min_score:
        for r in results:
            r[score_field] = max_val
        return results
    
    for r in results:
        raw = r.get(score_field, 0.0)
        normalized = (raw - min_score) / (max_score - min_score)
        r[score_field] = min_val + normalized * (max_val - min_val)
    
    return results