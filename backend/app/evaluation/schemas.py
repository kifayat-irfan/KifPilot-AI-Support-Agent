"""Schemas for Evaluation & Benchmark Suite."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    """Types of evaluation metrics."""
    PRECISION_AT_K = "precision_at_k"
    RECALL_AT_K = "recall_at_k"
    MRR = "mrr"
    NDCG = "ndcg"
    HIT_RATE = "hit_rate"
    CITATION_PRECISION = "citation_precision"
    CITATION_RECALL = "citation_recall"
    AVG_SIMILARITY = "avg_similarity"
    AVG_CONFIDENCE = "avg_confidence"
    HALLUCINATION_RATE = "hallucination_rate"
    AVG_RESPONSE_TIME = "avg_response_time"
    AVG_RETRIEVAL_TIME = "avg_retrieval_time"
    AVG_GENERATION_TIME = "avg_generation_time"
    AVG_TOKEN_USAGE = "avg_token_usage"


class BenchmarkItem(BaseModel):
    """Single benchmark item with expected results."""
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., description="Unique identifier for the benchmark item")
    question: str = Field(..., description="User question")
    expected_answer: str = Field(..., description="Expected/reference answer")
    expected_documents: List[str] = Field(default_factory=list, description="Expected document IDs")
    expected_pages: List[int] = Field(default_factory=list, description="Expected page numbers")
    expected_sections: List[str] = Field(default_factory=list, description="Expected section names")
    category: Optional[str] = Field(None, description="Category for grouping")
    difficulty: Optional[str] = Field(None, description="Difficulty level")
    tags: List[str] = Field(default_factory=list, description="Tags for filtering")


class BenchmarkDataset(BaseModel):
    """Benchmark dataset containing multiple items."""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Dataset name")
    version: str = Field(..., description="Dataset version")
    description: Optional[str] = None
    items: List[BenchmarkItem] = Field(..., description="Benchmark items")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class EvaluationResult(BaseModel):
    """Result of evaluating a single question."""
    model_config = ConfigDict(extra="allow")

    benchmark_id: str
    question: str
    predicted_answer: str
    expected_answer: str
    
    # Retrieval metrics
    retrieved_docs: List[str] = Field(default_factory=list)
    expected_docs: List[str] = Field(default_factory=list)
    precision_at_5: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    hit_rate: float = 0.0
    
    # Citation metrics
    predicted_citations: List[Dict[str, Any]] = Field(default_factory=list)
    expected_citations: List[Dict[str, Any]] = Field(default_factory=list)
    citation_precision: float = 0.0
    citation_recall: float = 0.0
    
    # Answer quality metrics
    similarity_score: float = 0.0
    confidence_score: float = 0.0
    hallucination_rate: float = 0.0
    
    # Performance metrics
    response_time_ms: float = 0.0
    retrieval_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    token_usage: int = 0
    
    # Metadata
    model_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BenchmarkResult(BaseModel):
    """Aggregated benchmark results."""
    model_config = ConfigDict(extra="allow")

    dataset_name: str
    dataset_version: str
    total_questions: int
    evaluated_questions: int
    
    # Aggregate metrics
    precision_at_5: float = 0.0
    recall_at_10: float = 0.0
    mrr: float = 0.0
    ndcg: float = 0.0
    hit_rate: float = 0.0
    citation_precision: float = 0.0
    citation_recall: float = 0.0
    avg_similarity: float = 0.0
    avg_confidence: float = 0.0
    hallucination_rate: float = 0.0
    avg_response_time_ms: float = 0.0
    avg_retrieval_time_ms: float = 0.0
    avg_generation_time_ms: float = 0.0
    avg_token_usage: float = 0.0
    
    # Per-question results
    results: List[EvaluationResult] = Field(default_factory=list)
    
    # Configuration
    model_name: Optional[str] = None
    embedding_model: Optional[str] = None
    hybrid_search_enabled: bool = False
    reranker_enabled: bool = False
    query_expansion_enabled: bool = False
    context_compression_enabled: bool = False
    
    # Timestamps
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    total_time_ms: float = 0.0


class BenchmarkRun(BaseModel):
    """A single benchmark run with configuration and results."""
    model_config = ConfigDict(extra="allow")

    id: str = Field(..., description="Unique run ID")
    name: str = Field(..., description="Run name")
    dataset_name: str
    dataset_version: str
    configuration: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[BenchmarkResult] = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RegressionComparison(BaseModel):
    """Comparison between two benchmark runs."""
    model_config = ConfigDict(extra="allow")

    current_run_id: str
    baseline_run_id: str
    
    # Metric comparisons
    metric_changes: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    # e.g., {"precision_at_5": {"current": 0.85, "baseline": 0.82, "delta": 0.03, "improved": true}}
    
    # Summary
    improved_metrics: List[str] = Field(default_factory=list)
    regressed_metrics: List[str] = Field(default_factory=list)
    unchanged_metrics: List[str] = Field(default_factory=list)
    
    # Overall assessment
    overall_improved: bool = False
    summary: str = ""


class LeaderboardEntry(BaseModel):
    """Leaderboard entry for benchmark history."""
    model_config = ConfigDict(extra="forbid")

    run_id: str
    name: str
    dataset_name: str
    dataset_version: str
    
    # Key metrics
    precision_at_5: float
    recall_at_10: float
    mrr: float
    ndcg: float
    citation_precision: float
    citation_recall: float
    hallucination_rate: float
    avg_response_time_ms: float
    
    # Configuration
    model_name: Optional[str] = None
    embedding_model: Optional[str] = None
    hybrid_search_enabled: bool = False
    reranker_enabled: bool = False
    query_expansion_enabled: bool = False
    context_compression_enabled: bool = False
    
    # Timestamp
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BenchmarkConfig(BaseModel):
    """Configuration for running a benchmark."""
    model_config = ConfigDict(extra="forbid")

    dataset_path: str = Field(..., description="Path to benchmark dataset (JSON/CSV)")
    output_path: str = Field(default="./benchmark_results", description="Output directory")
    output_formats: List[Literal["json", "csv", "markdown"]] = Field(default=["json", "markdown"])
    model_name: Optional[str] = None
    max_questions: Optional[int] = None
    timeout_seconds: float = 300.0
    parallel: bool = False
    max_workers: int = 4
    compare_with_baseline: bool = False
    baseline_run_id: Optional[str] = None
    save_raw_results: bool = True


class EvaluationRequest(BaseModel):
    """Request for evaluating a single answer."""
    model_config = ConfigDict(extra="forbid")

    question: str
    predicted_answer: str
    expected_answer: str
    retrieved_docs: List[str] = Field(default_factory=list)
    expected_docs: List[str] = Field(default_factory=list)
    predicted_citations: List[Dict[str, Any]] = Field(default_factory=list)
    expected_citations: List[Dict[str, Any]] = Field(default_factory=list)
    similarity_score: Optional[float] = None
    confidence_score: Optional[float] = None
    response_time_ms: Optional[float] = None
    retrieval_time_ms: Optional[float] = None
    generation_time_ms: Optional[float] = None
    token_usage: Optional[int] = None