"""Metrics calculation for evaluation and benchmarking."""

import math
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter
import logging

logger = logging.getLogger(__name__)


def precision_at_k(retrieved: List[str], relevant: List[str], k: int = 5) -> float:
    """
    Calculate Precision@K.
    
    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: List of relevant document IDs
        k: Number of top results to consider
        
    Returns:
        Precision@K score (0-1)
    """
    if not retrieved or not relevant or k <= 0:
        return 0.0
    
    top_k = retrieved[:k]
    relevant_set = set(relevant)
    hits = sum(1 for doc in top_k if doc in relevant_set)
    return hits / min(k, len(top_k))


def recall_at_k(retrieved: List[str], relevant: List[str], k: int = 10) -> float:
    """
    Calculate Recall@K.
    
    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: List of relevant document IDs
        k: Number of top results to consider
        
    Returns:
        Recall@K score (0-1)
    """
    if not relevant or not retrieved or k <= 0:
        return 0.0
    
    top_k = retrieved[:k]
    relevant_set = set(relevant)
    hits = sum(1 for doc in top_k if doc in relevant_set)
    return hits / len(relevant_set) if relevant_set else 0.0


def mean_reciprocal_rank(retrieved: List[str], relevant: List[str]) -> float:
    """
    Calculate Mean Reciprocal Rank (MRR).
    
    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: List of relevant document IDs
        
    Returns:
        MRR score (0-1)
    """
    if not retrieved or not relevant:
        return 0.0
    
    relevant_set = set(relevant)
    for i, doc in enumerate(retrieved):
        if doc in relevant_set:
            return 1.0 / (i + 1)
    return 0.0


def ndcg_at_k(retrieved: List[str], relevant: List[str], k: int = 10, 
              relevance_scores: Optional[Dict[str, float]] = None) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain (NDCG)@K.
    
    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: List of relevant document IDs
        k: Number of top results to consider
        relevance_scores: Optional dict mapping doc_id to relevance score (0-1)
        
    Returns:
        NDCG@K score (0-1)
    """
    if not retrieved or not relevant or k <= 0:
        return 0.0
    
    top_k = retrieved[:k]
    
    # Binary relevance if no scores provided
    if relevance_scores is None:
        relevance_scores = {doc: 1.0 for doc in relevant}
    
    # DCG calculation
    dcg = 0.0
    for i, doc in enumerate(top_k):
        rel = relevance_scores.get(doc, 0.0)
        if rel > 0:
            dcg += rel / math.log2(i + 2)
    
    # IDCG calculation (ideal DCG)
    ideal_scores = sorted(relevance_scores.values(), reverse=True)[:k]
    idcg = 0.0
    for i, rel in enumerate(ideal_scores):
        idcg += rel / math.log2(i + 2)
    
    if idcg == 0:
        return 0.0
    
    return dcg / idcg


def hit_rate(retrieved: List[str], relevant: List[str], k: int = 10) -> float:
    """
    Calculate Hit Rate@K (whether at least one relevant doc is in top K).
    
    Args:
        retrieved: List of retrieved document IDs (ordered by relevance)
        relevant: List of relevant document IDs
        k: Number of top results to consider
        
    Returns:
        Hit Rate (0 or 1)
    """
    if not retrieved or not relevant or k <= 0:
        return 0.0
    
    top_k = retrieved[:k]
    relevant_set = set(relevant)
    return 1.0 if any(doc in relevant_set for doc in top_k) else 0.0


def citation_precision(predicted: List[Dict[str, Any]], 
                      expected: List[Dict[str, Any]]) -> float:
    """
    Calculate citation precision.
    
    Args:
        predicted: List of predicted citations with doc_id/chunk_id
        expected: List of expected citations
        
    Returns:
        Citation precision (0-1)
    """
    if not predicted:
        return 0.0
    
    pred_ids = set()
    for c in predicted:
        cid = c.get("chunk_id") or c.get("document_id")
        if cid:
            pred_ids.add(cid)
    
    exp_ids = set()
    for c in expected:
        cid = c.get("chunk_id") or c.get("document_id")
        if cid:
            exp_ids.add(cid)
    
    if not exp_ids:
        return 1.0 if not pred_ids else 0.0
    
    hits = len(pred_ids & exp_ids)
    return hits / len(pred_ids) if pred_ids else 0.0


def citation_recall(predicted: List[Dict[str, Any]], 
                   expected: List[Dict[str, Any]]) -> float:
    """
    Calculate citation recall.
    
    Args:
        predicted: List of predicted citations with doc_id/chunk_id
        expected: List of expected citations
        
    Returns:
        Citation recall (0-1)
    """
    if not expected:
        return 1.0
    
    pred_ids = set()
    for c in predicted:
        cid = c.get("chunk_id") or c.get("document_id")
        if cid:
            pred_ids.add(cid)
    
    exp_ids = set()
    for c in expected:
        cid = c.get("chunk_id") or c.get("document_id")
        if cid:
            exp_ids.add(cid)
    
    if not exp_ids:
        return 1.0
    
    hits = len(pred_ids & exp_ids)
    return hits / len(exp_ids) if exp_ids else 0.0


def semantic_similarity(text1: str, text2: str) -> float:
    """
    Calculate semantic similarity between two texts.
    This is a placeholder - in production, use embeddings or BERTScore.
    
    Args:
        text1: First text
        text2: Second text
        
    Returns:
        Similarity score (0-1)
    """
    # Simple word overlap as fallback
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 and not words2:
        return 1.0
    if not words1 or not words2:
        return 0.0
    
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union) if union else 0.0


def hallucination_rate(predicted: str, expected: str, 
                      retrieved_context: Optional[str] = None) -> float:
    """
    Estimate hallucination rate.
    This is a placeholder - in production, use a dedicated hallucination detector.
    
    Args:
        predicted: Predicted answer
        expected: Expected/reference answer
        retrieved_context: Optional context used for generation
        
    Returns:
        Estimated hallucination rate (0-1)
    """
    # Placeholder - in production use a trained hallucination detector
    # For now, return 0 if predicted is subset of expected+context
    if not predicted:
        return 0.0
    
    # Simple heuristic: if predicted contains info not in expected or context
    pred_words = set(predicted.lower().split())
    expected_words = set(expected.lower().split())
    context_words = set(retrieved_context.lower().split()) if retrieved_context else set()
    
    allowed_words = expected_words | context_words
    if not allowed_words:
        return 0.0
    
    hallucinated = pred_words - allowed_words
    return len(hallucinated) / len(pred_words) if pred_words else 0.0


def aggregate_metrics(results: List[Dict[str, float]]) -> Dict[str, float]:
    """
    Aggregate metrics across multiple evaluations.
    
    Args:
        results: List of metric dictionaries
        
    Returns:
        Dictionary with mean, std, min, max for each metric
    """
    if not results:
        return {}
    
    all_keys = set()
    for r in results:
        all_keys.update(r.keys())
    
    aggregated = {}
    for key in all_keys:
        values = [r[key] for r in results if key in r and isinstance(r[key], (int, float))]
        if values:
            aggregated[f"{key}_mean"] = sum(values) / len(values)
            aggregated[f"{key}_std"] = math.stdev(values) if len(values) > 1 else 0.0
            aggregated[f"{key}_min"] = min(values)
            aggregated[f"{key}_max"] = max(values)
            aggregated[f"{key}_count"] = len(values)
    
    return aggregated


def compare_metrics(current: Dict[str, float], baseline: Dict[str, float], 
                   threshold: float = 0.01) -> Dict[str, Dict[str, Any]]:
    """
    Compare current metrics with baseline.
    
    Args:
        current: Current metric values
        baseline: Baseline metric values
        threshold: Minimum delta to consider significant
        
    Returns:
        Dictionary with comparison results
    """
    all_keys = set(current.keys()) | set(baseline.keys())
    comparison = {}
    
    for key in all_keys:
        curr = current.get(key, 0.0)
        base = baseline.get(key, 0.0)
        delta = curr - base
        
        improved = delta > threshold
        regressed = delta < -threshold
        
        comparison[key] = {
            "current": curr,
            "baseline": base,
            "delta": delta,
            "improved": improved,
            "regressed": regressed,
            "significant": abs(delta) > threshold,
        }
    
    return comparison


class MetricCalculator:
    """Utility class for calculating all metrics at once."""
    
    def __init__(self, k_precision: int = 5, k_recall: int = 10, k_ndcg: int = 10):
        self.k_precision = k_precision
        self.k_recall = k_recall
        self.k_ndcg = k_ndcg
    
    def calculate_all(self, retrieved: List[str], relevant: List[str],
                     predicted_answer: str, expected_answer: str,
                     predicted_citations: List[Dict] = None,
                     expected_citations: List[Dict] = None,
                     similarity_score: float = None,
                     confidence_score: float = None,
                     response_time_ms: float = None,
                     retrieval_time_ms: float = None,
                     generation_time_ms: float = None,
                     token_usage: int = None) -> Dict[str, float]:
        """Calculate all metrics at once."""
        
        metrics = {}
        
        # Retrieval metrics
        metrics["precision_at_5"] = precision_at_k(retrieved, relevant, self.k_precision)
        metrics["recall_at_10"] = recall_at_k(retrieved, relevant, self.k_recall)
        metrics["mrr"] = mean_reciprocal_rank(retrieved, relevant)
        metrics["ndcg"] = ndcg_at_k(retrieved, relevant, self.k_ndcg)
        metrics["hit_rate"] = hit_rate(retrieved, relevant, 10)
        
        # Citation metrics
        if predicted_citations is not None and expected_citations is not None:
            metrics["citation_precision"] = citation_precision(predicted_citations, expected_citations)
            metrics["citation_recall"] = citation_recall(predicted_citations, expected_citations)
        
        # Answer quality metrics
        if similarity_score is not None:
            metrics["similarity_score"] = similarity_score
        else:
            metrics["similarity_score"] = semantic_similarity(predicted_answer, expected_answer)
        
        if confidence_score is not None:
            metrics["confidence_score"] = confidence_score
        
        if predicted_answer and expected_answer:
            metrics["hallucination_rate"] = hallucination_rate(predicted_answer, expected_answer)
        
        # Performance metrics
        if response_time_ms is not None:
            metrics["response_time_ms"] = response_time_ms
        if retrieval_time_ms is not None:
            metrics["retrieval_time_ms"] = retrieval_time_ms
        if generation_time_ms is not None:
            metrics["generation_time_ms"] = generation_time_ms
        if token_usage is not None:
            metrics["token_usage"] = token_usage
        
        return metrics


# Import math at the top level
import math
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter