# Monitoring Stack

## Overview

Comprehensive observability with Prometheus metrics, OpenTelemetry tracing, structured logging, and health checks.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MONITORING STACK                                    │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │   Application   │───▶│  OpenTelemetry  │───▶│   Jaeger / Zipkin       │ │
│  │   (FastAPI)     │    │   SDK           │    │   (Distributed Tracing) │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘ │
│         │                       │                       │                 │
│         ▼                       ▼                       ▼                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │  Prometheus     │    │   Structured    │    │   Grafana / Loki        │ │
│  │  Client         │    │   Logging       │    │   (Dashboards/Logs)     │ │
│  │  (Metrics)      │    │   (JSON)        │    │                         │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘ │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    HEALTH CHECKS                                     │   │
│  │  /health  /api/v1/health  /api/v1/ollama/health  /chat/stream/health│   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Metrics (Prometheus)

```python
# monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary

# HTTP Metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status_code"]
)

http_request_duration = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_requests_in_flight = Gauge(
    "http_requests_in_flight",
    "HTTP requests currently being processed",
    ["method", "endpoint"]
)

http_request_size = Histogram(
    "http_request_size_bytes",
    "HTTP request size",
    ["method", "endpoint"]
)

http_response_size = Histogram(
    "http_response_size_bytes",
    "HTTP response size",
    ["method", "endpoint"]
)

# AI/ML Metrics
ai_embedding_time = Histogram(
    "ai_embedding_time_seconds",
    "Embedding generation time",
    ["model"]
)

ai_generation_time = Histogram(
    "ai_generation_time_seconds",
    "LLM generation time",
    ["model", "streaming"]
)

ai_streaming_duration = Histogram(
    "ai_streaming_duration_seconds",
    "Streaming response duration",
    ["model"]
)

ai_token_count = Counter(
    "ai_tokens_total",
    "Total tokens processed",
    ["model", "type"]  # prompt, completion
)

ai_prompt_tokens = Histogram(
    "ai_prompt_tokens",
    "Prompt token count",
    ["model"]
)

ai_completion_tokens = Histogram(
    "ai_completion_tokens",
    "Completion token count",
    ["model"]
)

# Retrieval Metrics
retrieval_search_time = Histogram(
    "retrieval_search_time_seconds",
    "Retrieval search time",
    ["type"]  # vector, bm25, hybrid, rerank
)

retrieval_results_count = Histogram(
    "retrieval_results_count",
    "Number of results returned"
)

retrieval_rerank_time = Histogram(
    "retrieval_rerank_time_seconds",
    "Cross-encoder rerank time"
)

retrieval_rrf_time = Histogram(
    "retrieval_rrf_time_seconds",
    "RRF fusion time"
)

# RAG Metrics
rag_query_time = Histogram(
    "rag_query_time_seconds",
    "RAG query time"
)

rag_confidence = Histogram(
    "rag_confidence",
    "Answer confidence score"
)

rag_citations_count = Histogram(
    "rag_citations_count",
    "Citations per answer"
)

rag_guardrails_triggered = Counter(
    "rag_guardrails_triggered_total",
    "Guardrails triggered",
    ["type"]  # input, output
)

# Document Metrics
documents_uploaded = Counter(
    "documents_uploaded_total",
    "Documents uploaded",
    ["status", "mime_type"]
)

document_processing_time = Histogram(
    "document_processing_seconds",
    "Document processing time",
    ["stage"]  # extract, chunk, embed, index
)

document_chunks_created = Histogram(
    "document_chunks_created",
    "Chunks per document"
)

# Vector Store Metrics
vector_search_time = Histogram(
    "vector_search_time_seconds",
    "Vector search time",
    ["collection"]
)

vector_add_time = Histogram(
    "vector_add_time_seconds",
    "Vector add time",
    ["collection"]
)

vector_collection_count = Gauge(
    "vector_collection_count",
    "Number of collections"
)

vector_document_count = Gauge(
    "vector_document_count",
    "Number of vectors per collection",
    ["collection"]
)

# Business Metrics
chat_sessions_active = Gauge(
    "chat_sessions_active",
    "Active chat sessions"
)

chat_messages_total = Counter(
    "chat_messages_total",
    "Total chat messages",
    ["role"]  # user, assistant
)

documents_uploaded = Counter(
    "documents_uploaded_total",
    "Documents uploaded",
    ["org_id"]
)

search_queries_total = Counter(
    "search_queries_total",
    "Search queries",
    ["type"]  # vector, hybrid, bm25
)

# Infrastructure Metrics
cpu_usage = Gauge("cpu_usage_percent", "CPU usage")
memory_usage = Gauge("memory_usage_bytes", "Memory usage")
memory_available = Gauge("memory_available_bytes", "Available memory")
disk_usage = Gauge("disk_usage_percent", "Disk usage")
disk_read_bytes = Counter("disk_read_bytes_total", "Disk read bytes")
disk_write_bytes = Counter("disk_write_bytes_total", "Disk write bytes")
network_receive_bytes = Counter("network_receive_bytes_total", "Network receive")
network_transmit_bytes = Counter("network_transmit_bytes_total", "Network transmit")

# Database Metrics
db_connections = Gauge("db_connections_active", "Active database connections")
db_query_duration = Histogram(
    "db_query_duration_seconds",
    "Database query duration",
    ["query_type"]
)
db_query_errors = Counter("db_query_errors_total", "Database query errors")

# Ollama Metrics
ollama_models_loaded = Gauge("ollama_models_loaded", "Loaded Ollama models")
ollama_generation_duration = Histogram(
    "ollama_generation_duration_seconds",
    "Ollama generation time"
)
ollama_embedding_duration = Histogram(
    "ollama_embedding_duration_seconds",
    "Ollama embedding time"
)
ollama_memory_usage = Gauge("ollama_memory_bytes", "Ollama memory usage")
```

## Middleware for Metrics

```python
# monitoring/middleware.py
class MonitoringMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        
        # In-flight
        http_requests_in_flight.labels(
            method=request.method,
            endpoint=request.url.path
        ).inc()
        
        # Request size
        content_length = request.headers.get("content-length")
        if content_length:
            http_request_size.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(int(content_length))
        
        try:
            response = await call_next(request)
            
            # Response size
            if hasattr(response, "headers"):
                cl = response.headers.get("content-length")
                if cl:
                    http_response_size.labels(
                        method=request.method,
                        endpoint=request.url.path
                    ).observe(int(cl))
            
            return response
            
        except Exception as e:
            # Track errors
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=500
            ).inc()
            raise
            
        finally:
            # Duration
            duration = time.perf_counter() - start
            http_request_duration.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
            
            # Total requests
            status = getattr(response, "status_code", 500) if 'response' in locals() else 500
            http_requests_total.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=status
            ).inc()
            
            # In-flight
            http_requests_in_flight.labels(
                method=request.method,
                endpoint=request.url.path
            ).dec()
```

## Tracing (OpenTelemetry)

```python
# monitoring/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.jaeger.proto.grpc import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def setup_tracing(
    service_name: str = "kifpilot",
    otlp_endpoint: str = "http://otel-collector:4317",
    jaeger_endpoint: str = "http://jaeger:14268/api/traces"
):
    # Provider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    
    # OTLP Exporter
    otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    
    # Jaeger Exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger",
        agent_port=6831
    )
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    
    # Auto-instrumentation
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    HTTPXClientInstrumentor().instrument()
    RedisInstrumentor().instrument()
    
    return trace.get_tracer(__name__)

# Usage in services
tracer = trace.get_tracer(__name__)

@tracer.start_as_current_span("retrieval.hybrid_search")
async def hybrid_search(query: str, top_k: int):
    with tracer.start_as_current_span("retrieval.vector") as span:
        vector_results = await vector_search(query, top_k)
        span.set_attribute("results.count", len(vector_results))
        span.set_attribute("query.length", len(query))
    
    with tracer.start_as_current_span("retrieval.bm25") as span:
        bm25_results = await bm25_search(query, top_k)
        span.set_attribute("results.count", len(bm25_results))
    
    with tracer.start_as_current_span("retrieval.rrf") as span:
        fused = rrf_fusion(vector_results, bm25_results)
        span.set_attribute("results.count", len(fused))
    
    return fused
```

## Structured Logging

```python
# monitoring/logging.py
import structlog
import logging
import sys

def setup_logging(level: str = "INFO", json_format: bool = True):
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper())
    )
    
    # Configure structlog
    if json_format:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer()
        ]
    else:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.dev.ConsoleRenderer(colors=True)
        ]
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True
    )

def get_logger(name: str) -> structlog.BoundLogger:
    return structlog.get_logger(name)

# Usage
logger = get_logger(__name__)

logger.info(
    "Request started",
    request_id="abc-123",
    method="POST",
    path="/api/v1/chat/stream",
    user_id="user-123"
)

logger.error(
    "Generation failed",
    request_id="abc-123",
    error="Timeout",
    model="qwen3.5:4b"
)
```

## Health Checks

```python
# monitoring/health.py
class HealthChecker:
    def __init__(
        self,
        db_session_factory,
        vector_store: VectorStoreService,
        ollama_client: OllamaClient
    ):
        self.db = db_session_factory
        self.vector = vector_store
        self.ollama = ollama_client
    
    async def check_all(self) -> HealthCheckResponse:
        checks = await asyncio.gather(
            self.check_database(),
            self.check_vector_store(),
            self.check_embedding_service(),
            self.check_ollama_service(),
            self.check_chromadb(),
            self.check_disk_space(),
            self.check_memory(),
            self.check_cpu(),
            return_exceptions=True
        )
        
        results = {
            "database": checks[0],
            "vector_store": checks[1],
            "embedding_service": checks[2],
            "ollama": checks[3],
            "chromadb": checks[4],
            "disk": checks[5],
            "memory": checks[6],
            "cpu": checks[7]
        }
        
        healthy = all(
            isinstance(r, ComponentHealth) and r.status == "healthy"
            for r in results.values()
        )
        
        return HealthCheckResponse(
            status="healthy" if healthy else "unhealthy",
            timestamp=datetime.utcnow().isoformat() + "Z",
            checks=results
        )
    
    async def check_database(self) -> ComponentHealth:
        try:
            async with self.db() as session:
                await session.execute(text("SELECT 1"))
            return ComponentHealth(status="healthy", message="Database connected")
        except Exception as e:
            return ComponentHealth(status="unhealthy", message=str(e))
    
    async def check_vector_store(self) -> ComponentHealth:
        try:
            collections = await self.vector.list_collections()
            return ComponentHealth(
                status="healthy",
                message=f"ChromaDB accessible, {len(collections)} collections"
            )
        except Exception as e:
            return ComponentHealth(status="unhealthy", message=str(e))
    
    async def check_ollama_service(self) -> ComponentHealth:
        try:
            health = await self.ollama.health_check()
            if health.healthy:
                return ComponentHealth(
                    status="healthy",
                    message=f"Ollama running, {len(health.models)} models"
                )
            return ComponentHealth(status="unhealthy", message="Ollama unhealthy")
        except Exception as e:
            return ComponentHealth(status="unhealthy", message=str(e))
```

## Health Endpoints

```python
# presentation/api/v1/routes/health.py
@router.get("/health")
async def health_check(
    health_checker: HealthChecker = Depends(get_health_checker)
):
    return await health_checker.check_all()

@router.get("/health/live")
async def liveness():
    return {"status": "alive"}

@router.get("/health/ready")
async def readiness(
    health_checker: HealthChecker = Depends(get_health_checker)
):
    result = await health_checker.check_all()
    if result.status == "healthy":
        return result
    return JSONResponse(status_code=503, content=result.dict())

@router.get("/api/v1/health")
async def api_health():
    return {"status": "healthy", "service": "KifPilot AI Support Agent"}

@router.get("/api/v1/ollama/health")
async def ollama_health(
    ollama: OllamaClient = Depends(get_ollama_client)
):
    return await ollama.health_check()
```

## Grafana Dashboards

```json
{
  "dashboard": {
    "title": "KifPilot Overview",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {"expr": "rate(http_requests_total[5m])", "legendFormat": "{{method}} {{endpoint}}"}
        ]
      },
      {
        "title": "Latency (p95)",
        "type": "graph",
        "targets": [
          {"expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))", "legendFormat": "p95"}
        ]
      },
      {
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {"expr": "rate(http_requests_total{status_code=~\"5..\"}[5m])", "legendFormat": "5xx"}
        ]
      },
      {
        "title": "Active Streams",
        "type": "graph",
        "targets": [
          {"expr": "streaming_sessions_active", "legendFormat": "active"}
        ]
      },
      {
        "title": "RAG Confidence",
        "type": "graph",
        "targets": [
          {"expr": "avg(rag_confidence)", "legendFormat": "avg confidence"}
        ]
      },
      {
        "title": "Retrieval Time",
        "type": "graph",
        "targets": [
          {"expr": "histogram_quantile(0.95, rate(retrieval_search_time_seconds_bucket[5m]))", "legendFormat": "p95"}
        ]
      },
      {
        "title": "Ollama Memory",
        "type": "graph",
        "targets": [
          {"expr": "ollama_memory_usage / 1024 / 1024 / 1024", "legendFormat": "GB"}
        ]
      }
    ]
  }
}
```

## Alerting Rules

```yaml
groups:
- name: kifpilot-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate (>5%)"
      
  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 5
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High latency (p95 > 5s)"
      
  - alert: OllamaDown
    expr: up{job="ollama"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "Ollama service down"
      
  - alert: HighMemoryUsage
    expr: (memory_usage_bytes / memory_available_bytes) > 0.9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Memory usage > 90%"
      
  - alert: DiskSpaceLow
    expr: (disk_free_bytes / disk_total_bytes) < 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Disk space < 10%"
      
  - alert: StreamingStuck
    expr: time() - streaming_last_token_timestamp > 60
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Streaming stalled > 60s"
```