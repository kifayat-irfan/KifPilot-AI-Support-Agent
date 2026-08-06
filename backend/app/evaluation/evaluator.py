"""Evaluator for benchmarking retrieval and generation quality."""

import time
import json
import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.evaluation.schemas import (
    BenchmarkItem,
    EvaluationResult,
    BenchmarkResult,
    BenchmarkConfig,
)
from app.evaluation.metrics import MetricCalculator
from app.services.retrieval import retrieval_service
from app.services.hybrid_search import hybrid_search_service
from app.services.hybrid_search.schemas import HybridSearchRequest
from app.services.reranker import reranker_service
from app.services.query_expansion import query_expander
from app.services.query_expansion.schemas import QueryExpansionConfig
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


@dataclass
class EvaluationContext:
    """Context for a single evaluation."""
    benchmark_item: "BenchmarkItem"
    config: "EvaluationConfig"
    start_time: float = field(default_factory=time.time)


class EvaluationConfig:
    """Configuration for evaluation."""
    def __init__(
        self,
        top_k: int = 5,
        enable_reranking: bool = False,
        enable_query_expansion: bool = False,
        enable_context_compression: bool = False,
        similarity_threshold: float = 0.7,
    ):
        self.top_k = top_k
        self.enable_reranking = enable_reranking
        self.enable_query_expansion = enable_query_expansion
        self.enable_context_compression = enable_context_compression
        self.similarity_threshold = similarity_threshold


class Evaluator:
    """Evaluates retrieval and generation quality against benchmarks."""
    
    def __init__(
        self,
        config: Optional[EvaluationConfig] = None,
        retrieval_service=None,
        reranker_service=None,
        query_expander=None,
    ):
        self.config = config or EvaluationConfig()
        self.retrieval_service = retrieval_service or retrieval_service
        self.reranker_service = reranker_service or reranker_service
        self.query_expander = query_expander or query_expander
        self.metric_calculator = MetricCalculator()
    
    async def evaluate_single(
        self,
        benchmark_item: "BenchmarkItem",
        organization_id: Optional[str] = None,
    ) -> EvaluationResult:
        """Evaluate a single benchmark item."""
        start_time = time.time()
        
        # Build the retrieval request
        hybrid_request = HybridSearchRequest(
            query=benchmark_item.question,
            top_k=self.config.top_k * 2,  # Get more for evaluation
            minimum_score=0.3,
            rrf_constant=60,
            vector_weight=1.0,
            bm25_weight=1.0,
            filters=None,
            include_vector_scores=True,
            include_bm25_scores=True,
        )
        
        # Execute hybrid search
        retrieval_start = time.time()
        hybrid_response = await hybrid_search_service.search(
            request=hybrid_request,
            organization_id=organization_id,
        )
        retrieval_time_ms = (time.time() - retrieval_start) * 1000
        
        if not hybrid_response.results:
            # No results found
            return EvaluationResult(
                benchmark_id=benchmark_item.id,
                question=benchmark_item.question,
                predicted_answer="No results found",
                expected_answer=benchmark_item.expected_answer,
                retrieval_time_ms=retrieval_time_ms,
                hallucination_rate=1.0,
            )
        
        # Get top results
        candidates = hybrid_response.results[:self.config.top_k * 2]
        
        # Reranking if enabled
        reranked_results = candidates
        if self.config.enable_reranking:
            try:
                from app.services.reranker import reranker_service
                reranked = await reranker_service.rerank_context(
                    query=benchmark_item.question,
                    candidates=candidates,
                    top_k=self.config.top_k,
                )
                if reranked:
                    reranked_results = reranked
            except Exception as e:
                logger.warning(f"Reranking failed: {e}")
        
        # Take top_k
        final_results = reranked_results[:self.config.top_k]
        
        # Generate answer (placeholder - in real implementation, use LLM)
        predicted_answer = self._generate_answer(benchmark_item.question, reranked_results)
        generation_time_ms = 0  # Placeholder
        
        # Calculate metrics
        retrieved_docs = [r.document_id for r in reranked_results]
        expected_docs = benchmark_item.expected_documents
        
        metrics = self.metric_calculator.calculate_all(
            retrieved=retrieved_docs,
            relevant=expected_docs,
            predicted_answer=self._generate_answer(benchmark_item.question, reranked_results),
            expected_answer=benchmark_item.expected_answer,
            predicted_citations=[{
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "score": r.similarity_score,
            } for r in reranked_results],
            expected_citations=[{"document_id": doc} for doc in expected_docs],
            similarity_score=None,  # Will be calculated
            confidence_score=None,
            response_time_ms=(time.time() - start_time) * 1000,
            retrieval_time_ms=retrieval_time_ms,
            generation_time_ms=generation_time_ms,
            token_usage=0,
        )
        
        return EvaluationResult(
            benchmark_id=benchmark_item.id,
            question=benchmark_item.question,
            predicted_answer=self._generate_answer(benchmark_item.question, reranked_results),
            expected_answer=benchmark_item.expected_answer,
            **metrics,
        )
    
    def _generate_answer(self, question: str, results: List) -> str:
        """Generate answer from retrieved results (placeholder)."""
        if not results:
            return "No relevant information found."
        
        # In production, this would use an LLM to generate the answer
        # For now, return a simple concatenation
        context_parts = []
        for r in results[:3]:
            text = r.text[:200] if r.text else ""
            if text:
                context_parts.append(f"[{r.document_name}] {text}")
        
        if not context_parts:
            return "No relevant information found."
        
        return "Based on the retrieved documents: " + " ".join(context_parts)


class BenchmarkRunner:
    """Runs complete benchmark suites."""
    
    def __init__(
        self,
        config: "BenchmarkConfig",
        evaluator: Optional[Evaluator] = None,
    ):
        self.config = config
        self.evaluator = evaluator or Evaluator()
        self.dataset_loader = None  # Will be set when running
    
    async def run(self) -> "BenchmarkResult":
        """Run the complete benchmark suite."""
        logger.info(f"Starting benchmark run: {self.config.dataset_path}")
        
        # Load dataset
        from app.evaluation.datasets import load_benchmark_dataset
        dataset = load_benchmark_dataset(self.config)
        logger.info(f"Loaded dataset: {dataset.name} v{dataset.version} ({len(dataset.items)} items)")
        
        # Limit questions if specified
        items = dataset.items
        if self.config.max_questions:
            items = items[:self.config.max_questions]
        
        results = []
        total_start = time.time()
        
        if self.config.parallel and len(items) > 1:
            results = await self._run_parallel(items)
        else:
            results = await self._run_sequential(items)
        
        # Aggregate results
        benchmark_result = self._aggregate_results(dataset.name, dataset.version, results)
        benchmark_result.completed_at = datetime.utcnow()
        benchmark_result.total_time_ms = (time.time() - total_start) * 1000
        
        return benchmark_result
    
    async def _run_sequential(self, items: List["BenchmarkItem"]) -> List[EvaluationResult]:
        """Run evaluations sequentially."""
        results = []
        for i, item in enumerate(items):
            logger.info(f"Evaluating {i+1}/{len(items)}: {item.id}")
            try:
                result = await self.evaluator.evaluate_single(item)
                results.append(result)
            except Exception as e:
                logger.error(f"Evaluation failed for {item.id}: {e}")
                # Add failed result
                results.append(EvaluationResult(
                    benchmark_id=item.id,
                    question=item.question,
                    predicted_answer=f"ERROR: {str(e)}",
                    expected_answer=item.expected_answer,
                    hallucination_rate=1.0,
                ))
        return results
    
    async def _run_parallel(self, items: List["BenchmarkItem"]) -> List[EvaluationResult]:
        """Run evaluations in parallel."""
        semaphore = asyncio.Semaphore(self.config.max_workers)
        
        async def evaluate_with_semaphore(item):
            async with semaphore:
                return await self.evaluator.evaluate_single(item)
        
        tasks = [evaluate_with_semaphore(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        results_list = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Evaluation failed for {items[i].id}: {result}")
                results_list.append(EvaluationResult(
                    benchmark_id=items[i].id,
                    question=items[i].question,
                    predicted_answer=f"ERROR: {str(result)}",
                    expected_answer=items[i].expected_answer,
                    hallucination_rate=1.0,
                ))
            else:
                results_list.append(result)
        
        return results_list
    
    def _aggregate_results(
        self,
        dataset_name: str,
        dataset_version: str,
        results: List[EvaluationResult],
    ) -> "BenchmarkResult":
        """Aggregate individual results into benchmark summary."""
        if not results:
            return BenchmarkResult(
                dataset_name=dataset_name,
                dataset_version=dataset_version,
                total_questions=0,
                evaluated_questions=0,
            )
        
        # Calculate aggregate metrics
        metric_keys = [
            "precision_at_5", "recall_at_10", "mrr", "ndcg", "hit_rate",
            "citation_precision", "citation_recall", "avg_similarity",
            "avg_confidence", "hallucination_rate",
            "avg_response_time_ms", "avg_retrieval_time_ms",
            "avg_generation_time_ms", "avg_token_usage",
        ]
        
        aggregated = {}
        for key in metric_keys:
            values = [getattr(r, key, 0.0) for r in results if hasattr(r, key)]
            if values:
                aggregated[key] = sum(values) / len(values)
            else:
                aggregated[key] = 0.0
        
        return BenchmarkResult(
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            total_questions=len(results),
            evaluated_questions=len(results),
            results=results,
            **aggregated,
        )


# Import necessary modules
from dataclasses import dataclass, field
import asyncio
import math
from typing import List, Dict, Any, Optional, Literal, Tuple
from datetime import datetime
from app.evaluation.schemas import (
    BenchmarkItem,
    EvaluationResult,
    BenchmarkResult,
    BenchmarkConfig,
)
from app.evaluation.metrics import MetricCalculator