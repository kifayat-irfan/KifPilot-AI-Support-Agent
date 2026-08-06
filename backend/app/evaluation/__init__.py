"""Evaluation & Benchmark Suite for KifPilot AI Support Agent."""

from app.evaluation.schemas import (
    MetricType,
    BenchmarkItem,
    BenchmarkDataset,
    EvaluationResult,
    BenchmarkResult,
    BenchmarkRun,
    BenchmarkConfig,
    EvaluationRequest,
    RegressionComparison,
    LeaderboardEntry,
)

from app.evaluation.metrics import (
    precision_at_k,
    recall_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    hit_rate,
    citation_precision,
    citation_recall,
    semantic_similarity,
    hallucination_rate,
    aggregate_metrics,
    compare_metrics,
    MetricCalculator,
)

from app.evaluation.datasets import (
    BenchmarkDatasetLoader,
    BenchmarkDatasetRegistry,
    load_benchmark_dataset,
)

from app.evaluation.evaluator import (
    Evaluator,
    EvaluationConfig,
    BenchmarkRunner,
)

from app.evaluation.benchmark import (
    BenchmarkSuite,
    run_benchmark_cli,
)

from app.evaluation.report import (
    ReportGenerator,
    report_generator,
)

from app.evaluation.runner import (
    run_benchmark,
    main,
)

__all__ = [
    # Schemas
    "MetricType",
    "BenchmarkItem",
    "BenchmarkDataset",
    "EvaluationResult",
    "BenchmarkResult",
    "BenchmarkRun",
    "BenchmarkConfig",
    "EvaluationRequest",
    "RegressionComparison",
    "LeaderboardEntry",
    # Metrics
    "precision_at_k",
    "recall_at_k",
    "mean_reciprocal_rank",
    "ndcg_at_k",
    "hit_rate",
    "citation_precision",
    "citation_recall",
    "semantic_similarity",
    "hallucination_rate",
    "aggregate_metrics",
    "compare_metrics",
    "MetricCalculator",
    # Datasets
    "BenchmarkDatasetLoader",
    "BenchmarkDatasetRegistry",
    "load_benchmark_dataset",
    # Evaluator
    "Evaluator",
    "EvaluationConfig",
    "BenchmarkRunner",
    # Benchmark
    "BenchmarkSuite",
    "run_benchmark_cli",
    # Report
    "ReportGenerator",
    "report_generator",
    # Runner
    "run_benchmark",
    "main",
]