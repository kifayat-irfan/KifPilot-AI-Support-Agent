"""Prometheus metrics collection for KifPilot."""

import time
import functools
from typing import Callable, Optional, Dict, Any, List
from contextlib import contextmanager
from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
from prometheus_client.core import CollectorRegistry as PrometheusCollectorRegistry
import logging
import time
import psutil
import os

from app.monitoring.schemas import (
    AIMetricNames, HTTPMetricNames, InfraMetricNames,
    MetricType, MetricPoint
)
from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Create a custom registry
registry = CollectorRegistry()

# ============================================================================
# HTTP Metrics
# ============================================================================

http_requests_total = Counter(
    HTTPMetricNames.REQUEST_COUNT,
    "Total HTTP requests",
    ["method", "endpoint", "status_code"],
    registry=registry
)

http_request_duration = Histogram(
    HTTPMetricNames.REQUEST_DURATION,
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

http_request_size = Histogram(
    HTTPMetricNames.REQUEST_SIZE,
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 1000000],
    registry=registry
)

http_response_size = Histogram(
    HTTPMetricNames.RESPONSE_SIZE,
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 500, 1000, 5000, 10000, 50000, 100000, 1000000],
    registry=registry
)

http_requests_in_flight = Gauge(
    HTTPMetricNames.REQUESTS_IN_FLIGHT,
    "Number of HTTP requests currently being processed",
    ["method", "endpoint"],
    registry=registry
)

# ============================================================================
# AI Metrics
# ============================================================================

ai_embedding_time = Histogram(
    AIMetricNames.EMBEDDING_TIME,
    "Time spent generating embeddings in seconds",
    ["model", "operation"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

ai_retrieval_time = Histogram(
    AIMetricNames.RETRIEVAL_TIME,
    "Time spent in retrieval in seconds",
    ["method", "collection"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

ai_hybrid_search_time = Histogram(
    AIMetricNames.HYBRID_SEARCH_TIME,
    "Time spent in hybrid search in seconds",
    ["query_type"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

ai_rrf_time = Histogram(
    AIMetricNames.RRF_TIME,
    "Time spent in RRF fusion in seconds",
    ["fusion_type"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
    registry=registry
)

ai_reranker_time = Histogram(
    AIMetricNames.RERANKER_TIME,
    "Time spent in cross-encoder reranking in seconds",
    ["model", "candidate_count"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

ai_context_compression_time = Histogram(
    AIMetricNames.CONTEXT_COMPRESSION_TIME,
    "Time spent in context compression in seconds",
    ["strategy", "chunk_count"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5],
    registry=registry
)

ai_generation_time = Histogram(
    AIMetricNames.GENERATION_TIME,
    "Time spent in LLM generation in seconds",
    ["model", "stream"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 25.0, 60.0, 120.0],
    registry=registry
)

ai_streaming_duration = Histogram(
    AIMetricNames.STREAMING_DURATION,
    "Total streaming duration in seconds",
    ["model"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0],
    registry=registry
)

# Token metrics
ai_token_count = Counter(
    AIMetricNames.TOKEN_COUNT,
    "Total tokens processed",
    ["type", "model"],
    registry=registry
)

ai_prompt_tokens = Counter(
    AIMetricNames.PROMPT_TOKENS,
    "Total prompt tokens",
    ["model"],
    registry=registry
)

ai_completion_tokens = Counter(
    AIMetricNames.COMPLETION_TOKENS,
    "Total completion tokens",
    ["model"],
    registry=registry
)

# Quality metrics
ai_similarity_score = Histogram(
    AIMetricNames.SIMILARITY_SCORE,
    "Similarity score of retrieved documents",
    ["retrieval_method"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry
)

ai_confidence_score = Histogram(
    AIMetricNames.CONFIDENCE_SCORE,
    "Confidence score of generated answers",
    ["model"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry
)

ai_hallucination_rate = Histogram(
    AIMetricNames.HALLUCINATION_RATE,
    "Hallucination rate of generated answers",
    ["model", "detection_method"],
    buckets=[0.0, 0.01, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 1.0],
    registry=registry
)

# Citation metrics
ai_citation_precision = Histogram(
    AIMetricNames.CITATION_PRECISION,
    "Citation precision score",
    ["retrieval_method"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry
)

ai_citation_recall = Histogram(
    AIMetricNames.CITATION_RECALL,
    "Citation recall score",
    ["retrieval_method"],
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
    registry=registry
)

# ============================================================================
# Infrastructure Metrics
# ============================================================================

cpu_usage = Gauge(
    InfraMetricNames.CPU_USAGE,
    "CPU usage percentage",
    ["instance"],
    registry=registry
)

memory_usage = Gauge(
    InfraMetricNames.MEMORY_USAGE,
    "Memory usage in bytes",
    ["instance", "type"],  # type: rss, vms, percent
    registry=registry
)

memory_available = Gauge(
    InfraMetricNames.MEMORY_AVAILABLE,
    "Available memory in bytes",
    ["instance"],
    registry=registry
)

disk_usage = Gauge(
    InfraMetricNames.DISK_USAGE,
    "Disk usage percentage",
    ["instance", "mount_point"],
    registry=registry
)

disk_read_bytes = Counter(
    InfraMetricNames.DISK_IO_READ,
    "Disk read bytes total",
    ["instance", "device"],
    registry=registry
)

disk_write_bytes = Counter(
    InfraMetricNames.DISK_IO_WRITE,
    "Disk write bytes total",
    ["instance", "device"],
    registry=registry
)

network_receive_bytes = Counter(
    InfraMetricNames.NETWORK_IO_RECEIVE,
    "Network receive bytes total",
    ["instance", "interface"],
    registry=registry
)

network_transmit_bytes = Counter(
    InfraMetricNames.NETWORK_IO_TRANSMIT,
    "Network transmit bytes total",
    ["instance", "interface"],
    registry=registry
)

# Database metrics
db_connections = Gauge(
    InfraMetricNames.DB_CONNECTIONS,
    "Active database connections",
    ["database", "state"],  # state: active, idle
    registry=registry
)

db_query_duration = Histogram(
    InfraMetricNames.DB_QUERY_DURATION,
    "Database query duration in seconds",
    ["database", "operation"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 5.0],
    registry=registry
)

db_query_errors = Counter(
    InfraMetricNames.DB_QUERY_ERRORS,
    "Database query errors total",
    ["database", "operation", "error_type"],
    registry=registry
)

# ChromaDB metrics
chromadb_collections = Gauge(
    InfraMetricNames.CHROMADB_COLLECTIONS,
    "Number of ChromaDB collections",
    ["instance"],
    registry=registry
)

chromadb_documents = Gauge(
    InfraMetricNames.CHROMADB_DOCUMENTS,
    "Total documents in ChromaDB",
    ["instance", "collection"],
    registry=registry
)

chromadb_query_duration = Histogram(
    InfraMetricNames.CHROMADB_QUERY_DURATION,
    "ChromaDB query duration in seconds",
    ["operation", "collection"],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
    registry=registry
)

# Ollama metrics
ollama_models_loaded = Gauge(
    InfraMetricNames.OLLAMA_MODELS_LOADED,
    "Number of Ollama models loaded",
    ["instance"],
    registry=registry
)

ollama_generation_duration = Histogram(
    InfraMetricNames.OLLAMA_GENERATION_DURATION,
    "Ollama generation duration in seconds",
    ["model", "stream"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
    registry=registry
)

ollama_embedding_duration = Histogram(
    InfraMetricNames.OLLAMA_EMBEDDING_DURATION,
    "Ollama embedding duration in seconds",
    ["model"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=registry
)

ollama_memory_usage = Gauge(
    InfraMetricNames.OLLAMA_MEMORY_USAGE,
    "Ollama memory usage in bytes",
    ["instance", "model"],
    registry=registry
)

# ============================================================================
# Custom Business Metrics
# ============================================================================

# Chat metrics
chat_sessions_active = Gauge(
    "chat_sessions_active",
    "Number of active chat sessions",
    ["organization_id"],
    registry=registry
)

chat_messages_total = Counter(
    "chat_messages_total",
    "Total chat messages",
    ["organization_id", "role"],  # role: user, assistant
    registry=registry
)

# Document metrics
documents_uploaded = Counter(
    "documents_uploaded_total",
    "Total documents uploaded",
    ["organization_id", "file_type", "status"],  # status: success, failed, processing
    registry=registry
)

documents_indexed = Counter(
    "documents_indexed_total",
    "Total documents indexed",
    ["organization_id", "status"],
    registry=registry
)

# Search metrics
search_queries_total = Counter(
    "search_queries_total",
    "Total search queries",
    ["organization_id", "search_type"],  # search_type: vector, bm25, hybrid
    registry=registry
)

search_results_returned = Histogram(
    "search_results_returned",
    "Number of search results returned",
    ["organization_id", "search_type"],
    buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 30, 50],
    registry=registry
)

# Organization metrics
organizations_active = Gauge(
    "organizations_active",
    "Number of active organizations",
    registry=registry
)

users_active = Gauge(
    "users_active",
    "Number of active users",
    ["organization_id"],
    registry=registry
)


# ============================================================================
# Helper Functions
# ============================================================================

def update_infrastructure_metrics():
    """Update infrastructure metrics from system."""
    try:
        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1)
        cpu_usage.labels(instance="localhost").set(cpu_percent)
        
        # Memory
        mem = psutil.virtual_memory()
        memory_usage.labels(instance="localhost", type="rss").set(psutil.Process().memory_info().rss)
        memory_usage.labels(instance="localhost", type="vms").set(psutil.Process().memory_info().vms)
        memory_usage.labels(instance="localhost", type="percent").set(mem.percent)
        memory_available.labels(instance="localhost").set(mem.available)
        
        # Disk
        disk = psutil.disk_usage('/')
        disk_usage.labels(instance="localhost", mount_point="/").set(disk.percent)
        
        # Network
        net = psutil.net_io_counters()
        network_receive_bytes.labels(instance="localhost", interface="all").inc(net.bytes_recv)
        network_transmit_bytes.labels(instance="localhost", interface="all").inc(net.bytes_sent)
        
    except Exception as e:
        logger.error(f"Failed to update infrastructure metrics: {e}")


def record_http_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration_seconds: float,
    request_size: int = 0,
    response_size: int = 0
):
    """Record HTTP request metrics."""
    endpoint_normalized = _normalize_endpoint(endpoint)
    
    http_requests_total.labels(
        method=method,
        endpoint=endpoint_normalized,
        status_code=str(status_code)
    ).inc()
    
    http_request_duration.labels(
        method=method,
        endpoint=endpoint_normalized
    ).observe(duration_seconds)
    
    if request_size > 0:
        http_request_size.labels(
            method=method,
            endpoint=endpoint_normalized
        ).observe(request_size)
    
    if response_size > 0:
        http_response_size.labels(
            method=method,
            endpoint=endpoint_normalized
        ).observe(response_size)


def _normalize_endpoint(path: str) -> str:
    """Normalize endpoint path for metrics grouping."""
    # Replace UUIDs, IDs with placeholders
    import re
    path = re.sub(r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', '/:uuid', path)
    path = re.sub(r'/\d+', '/:id', path)
    return path


@contextmanager
def track_ai_operation(
    metric: Histogram,
    labels: Dict[str, str],
    success: bool = True
):
    """Context manager to track AI operation duration."""
    start = time.perf_counter()
    error = None
    try:
        yield
    except Exception as e:
        error = e
        success = False
        raise
    finally:
        duration = time.perf_counter() - start
        labels_with_status = {**labels, "success": str(success).lower()}
        metric.labels(**labels_with_status).observe(duration_seconds)


def record_ai_tokens(model: str, prompt_tokens: int, completion_tokens: int):
    """Record token usage."""
    ai_token_count.labels(type="total", model=model).inc(prompt_tokens + completion_tokens)
    ai_token_count.labels(type="prompt", model=model).inc(prompt_tokens)
    ai_token_count.labels(type="completion", model=model).inc(completion_tokens)
    ai_prompt_tokens.labels(model=model).inc(prompt_tokens)
    ai_completion_tokens.labels(model=model).inc(completion_tokens)


def record_retrieval_metrics(
    method: str,
    collection: str,
    duration_seconds: float,
    result_count: int,
    scores: Optional[List[float]] = None
):
    """Record retrieval metrics."""
    ai_retrieval_time.labels(method=method, collection=collection).observe(duration_seconds)
    search_results_returned.labels(organization_id="default", search_type=method).observe(result_count)
    
    if scores:
        for score in scores:
            ai_similarity_score.labels(retrieval_method=method).observe(score)


def record_ai_generation(
    model: str,
    stream: bool,
    duration_seconds: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
    similarity_score: Optional[float] = None,
    confidence_score: Optional[float] = None,
    hallucinated: bool = False
):
    """Record AI generation metrics."""
    stream_label = "true" if stream else "false"
    
    ai_generation_time.labels(model=model, stream=stream_label).observe(duration_seconds)
    ai_streaming_duration.labels(model=model).observe(duration_seconds)
    
    if prompt_tokens > 0 or completion_tokens > 0:
        record_ai_tokens(model, prompt_tokens, completion_tokens)
    
    if similarity_score is not None:
        ai_similarity_score.labels(retrieval_method="generation").observe(similarity_score)
    
    if confidence_score is not None:
        ai_confidence_score.labels(model=model).observe(confidence_score)
    
    if hallucinated:
        ai_hallucination_rate.labels(model=model, detection_method="heuristic").observe(1.0)
    else:
        ai_hallucination_rate.labels(model=model, detection_method="heuristic").observe(0.0)


def get_metrics() -> bytes:
    """Get all metrics in Prometheus format."""
    return generate_latest(registry)


def get_content_type() -> str:
    """Get Prometheus content type."""
    return CONTENT_TYPE_LATEST