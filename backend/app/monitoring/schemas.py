"""Monitoring & Observability Schemas."""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class MetricType(str, Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricLabel(BaseModel):
    """Label for a metric."""
    model_config = ConfigDict(extra="forbid")

    name: str
    value: str


class MetricPoint(BaseModel):
    """A single metric data point."""
    model_config = ConfigDict(extra="forbid")

    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    help: Optional[str] = None


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class SpanStatus(str, Enum):
    """Span status for distributed tracing."""
    OK = "ok"
    ERROR = "error"


class ComponentHealth(BaseModel):
    """Health status of a component."""
    model_config = ConfigDict(extra="forbid")

    name: str
    status: HealthStatus
    message: Optional[str] = None
    latency_ms: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)
    last_check: datetime = Field(default_factory=datetime.utcnow)


class HealthCheckResponse(BaseModel):
    """Overall health check response."""
    model_config = ConfigDict(extra="forbid")

    status: HealthStatus
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    version: str = "1.0.0"
    uptime_seconds: float
    components: List[ComponentHealth] = Field(default_factory=list)


class TraceContext(BaseModel):
    """Distributed tracing context."""
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    sampled: bool = True
    baggage: Dict[str, str] = Field(default_factory=dict)


class SpanData(BaseModel):
    """Distributed tracing span."""
    model_config = ConfigDict(extra="forbid")

    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    operation_name: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    tags: Dict[str, str] = Field(default_factory=dict)
    logs: List[Dict[str, Any]] = Field(default_factory=list)
    status: Literal["ok", "error"] = "ok"
    error_message: Optional[str] = None


class LogEntry(BaseModel):
    """Structured log entry."""
    model_config = ConfigDict(extra="forbid")

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    message: str
    logger: str
    module: Optional[str] = None
    function: Optional[str] = None
    line: Optional[int] = None
    
    # Request context
    request_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    user_id: Optional[str] = None
    organization_id: Optional[str] = None
    session_id: Optional[str] = None
    
    # HTTP context
    method: Optional[str] = None
    path: Optional[str] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    
    # Additional context
    extra: Dict[str, Any] = Field(default_factory=dict)


class AlertRule(BaseModel):
    """Alert rule definition."""
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str
    severity: Literal["info", "warning", "critical"]
    metric_name: str
    condition: str  # e.g., "> 1000", "< 0.5"
    threshold: float
    duration_seconds: int = 300  # How long condition must persist
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class Alert(BaseModel):
    """Active alert."""
    model_config = ConfigDict(extra="forbid")

    rule_name: str
    severity: Literal["info", "warning", "critical"]
    message: str
    value: float
    threshold: float
    started_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = Field(default_factory=dict)
    annotations: Dict[str, str] = Field(default_factory=dict)


class DashboardPanel(BaseModel):
    """Grafana dashboard panel configuration."""
    model_config = ConfigDict(extra="forbid")

    title: str
    type: Literal["graph", "stat", "table", "heatmap", "logs", "piechart"]
    grid_pos: Dict[str, int]  # x, y, w, h
    targets: List[Dict[str, Any]]
    options: Dict[str, Any] = Field(default_factory=dict)
    field_config: Dict[str, Any] = Field(default_factory=dict)


class Dashboard(BaseModel):
    """Grafana dashboard."""
    model_config = ConfigDict(extra="forbid")

    uid: str
    title: str
    tags: List[str] = Field(default_factory=list)
    timezone: str = "utc"
    panels: List[DashboardPanel] = Field(default_factory=list)
    templating: Dict[str, Any] = Field(default_factory=dict)
    time: Dict[str, Any] = Field(default_factory=dict)
    refresh: str = "10s"


class PrometheusConfig(BaseModel):
    """Prometheus configuration."""
    model_config = ConfigDict(extra="forbid")

    global_config: Dict[str, Any] = Field(default_factory=dict)
    scrape_configs: List[Dict[str, Any]] = Field(default_factory=list)
    alerting: Dict[str, Any] = Field(default_factory=dict)
    rule_files: List[str] = Field(default_factory=list)
    remote_write: List[Dict[str, Any]] = Field(default_factory=list)
    remote_read: List[Dict[str, Any]] = Field(default_factory=list)


class GrafanaDatasource(BaseModel):
    """Grafana datasource configuration."""
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    url: str
    access: Literal["proxy", "direct"] = "proxy"
    basic_auth: bool = False
    basic_auth_user: Optional[str] = None
    basic_auth_password: Optional[str] = None
    json_data: Dict[str, Any] = Field(default_factory=dict)
    secure_json_data: Dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    editable: bool = False


class ExporterConfig(BaseModel):
    """Exporter configuration."""
    model_config = ConfigDict(extra="forbid")

    prometheus_port: int = 9090
    prometheus_path: str = "/metrics"
    otlp_endpoint: Optional[str] = None
    otlp_headers: Dict[str, str] = Field(default_factory=dict)
    jaeger_endpoint: Optional[str] = None
    zipkin_endpoint: Optional[str] = None


# AI-specific metric names
class AIMetricNames:
    """Standardized AI metric names."""
    
    # Retrieval metrics
    EMBEDDING_TIME = "ai_embedding_time_seconds"
    RETRIEVAL_TIME = "ai_retrieval_time_seconds"
    HYBRID_SEARCH_TIME = "ai_hybrid_search_time_seconds"
    RRF_TIME = "ai_rrf_time_seconds"
    RERANKER_TIME = "ai_reranker_time_seconds"
    CONTEXT_COMPRESSION_TIME = "ai_context_compression_time_seconds"
    GENERATION_TIME = "ai_generation_time_seconds"
    STREAMING_DURATION = "ai_streaming_duration_seconds"
    
    # Token metrics
    TOKEN_COUNT = "ai_token_count_total"
    PROMPT_TOKENS = "ai_prompt_tokens_total"
    COMPLETION_TOKENS = "ai_completion_tokens_total"
    
    # Quality metrics
    SIMILARITY_SCORE = "ai_similarity_score"
    CONFIDENCE_SCORE = "ai_confidence_score"
    HALLUCINATION_RATE = "ai_hallucination_rate"
    
    # Citation metrics
    CITATION_PRECISION = "ai_citation_precision"
    CITATION_RECALL = "ai_citation_recall"


# HTTP metric names
class HTTPMetricNames:
    """Standardized HTTP metric names."""
    
    REQUEST_COUNT = "http_requests_total"
    REQUEST_DURATION = "http_request_duration_seconds"
    REQUEST_SIZE = "http_request_size_bytes"
    RESPONSE_SIZE = "http_response_size_bytes"
    REQUESTS_IN_FLIGHT = "http_requests_in_flight"


# Infrastructure metric names
class InfraMetricNames:
    """Standardized infrastructure metric names."""
    
    CPU_USAGE = "system_cpu_usage_percent"
    MEMORY_USAGE = "system_memory_usage_bytes"
    MEMORY_AVAILABLE = "system_memory_available_bytes"
    DISK_USAGE = "system_disk_usage_percent"
    DISK_IO_READ = "system_disk_read_bytes_total"
    DISK_IO_WRITE = "system_disk_write_bytes_total"
    NETWORK_IO_RECEIVE = "system_network_receive_bytes_total"
    NETWORK_IO_TRANSMIT = "system_network_transmit_bytes_total"
    
    # Database
    DB_CONNECTIONS = "db_connections_active"
    DB_QUERY_DURATION = "db_query_duration_seconds"
    DB_QUERY_ERRORS = "db_query_errors_total"
    
    # ChromaDB
    CHROMADB_COLLECTIONS = "chromadb_collections_total"
    CHROMADB_DOCUMENTS = "chromadb_documents_total"
    CHROMADB_QUERY_DURATION = "chromadb_query_duration_seconds"
    
    # Ollama
    OLLAMA_MODELS_LOADED = "ollama_models_loaded"
    OLLAMA_GENERATION_DURATION = "ollama_generation_duration_seconds"
    OLLAMA_EMBEDDING_DURATION = "ollama_embedding_duration_seconds"
    OLLAMA_MEMORY_USAGE = "ollama_memory_usage_bytes"