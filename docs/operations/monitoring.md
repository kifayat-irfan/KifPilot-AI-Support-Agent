# Monitoring Guide

## Overview

Complete monitoring setup for KifPilot with Prometheus, Grafana, Jaeger, and Loki.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         MONITORING STACK                                    │
│                                                                             │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │   Application   │───▶│  Prometheus     │───▶│   Grafana               │ │
│  │   (FastAPI)     │    │  (Metrics)      │    │   (Dashboards)          │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘ │
│         │                       │                       │                 │
│         ▼                       ▼                       ▼                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────────────┐ │
│  │  OpenTelemetry  │    │   Alertmanager  │    │   Loki                  │ │
│  │  (Tracing)      │    │   (Alerts)      │    │   (Logs)                │ │
│  └─────────────────┘    └─────────────────┘    └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Prometheus Setup

### Deployment

```yaml
# prometheus.yaml
apiVersion: monitoring.coreos.com/v1
kind: Prometheus
metadata:
  name: kifpilot
  namespace: monitoring
spec:
  replicas: 2
  retention: 30d
  storage:
    volumeClaimTemplate:
      spec:
        storageClassName: fast-ssd
        resources:
          requests:
            storage: 200Gi
  serviceAccountName: prometheus
  serviceMonitorSelector:
    matchLabels:
      app: kifpilot
  ruleSelector:
    matchLabels:
      app: kifpilot
```

### ServiceMonitors

```yaml
# servicemonitor-backend.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: kifpilot-backend
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: kifpilot-backend
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
  namespaceSelector:
    matchNames:
    - kifpilot
```

### Key Metrics to Collect

```python
# Application metrics (already instrumented)
# HTTP
http_requests_total
http_request_duration_seconds
http_requests_in_flight

# AI/ML
ai_embedding_time_seconds
ai_generation_time_seconds
ai_streaming_duration_seconds
ai_token_count_total

# Retrieval
retrieval_search_time_seconds
retrieval_rerank_time_seconds
retrieval_rrf_time_seconds

# RAG
rag_query_time_seconds
rag_confidence
rag_citations_count

# Business
chat_sessions_active
documents_uploaded_total
search_queries_total

# Infrastructure
cpu_usage_percent
memory_usage_bytes
disk_usage_percent
db_connections_active
```

---

## Grafana Dashboards

### 1. Overview Dashboard

```json
{
  "title": "KifPilot Overview",
  "panels": [
    {
      "title": "Request Rate",
      "type": "graph",
      "targets": [
        {"expr": "sum(rate(http_requests_total[5m])) by (method, endpoint)", "legendFormat": "{{method}} {{endpoint}}"}
      ]
    },
    {
      "title": "Latency (p50, p95, p99)",
      "type": "graph",
      "targets": [
        {"expr": "histogram_quantile(0.50, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))", "legendFormat": "p50 {{endpoint}}"},
        {"expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))", "legendFormat": "p95 {{endpoint}}"},
        {"expr": "histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))", "legendFormat": "p99 {{endpoint}}"}
      ]
    },
    {
      "title": "Error Rate",
      "type": "graph",
      "targets": [
        {"expr": "sum(rate(http_requests_total{status=~\"5..\"}[5m])) by (endpoint)", "legendFormat": "5xx {{endpoint}}"},
        {"expr": "sum(rate(http_requests_total{status=~\"4..\"}[5m])) by (endpoint)", "legendFormat": "4xx {{endpoint}}"}
      ]
    },
    {
      "title": "Active Streams",
      "type": "stat",
      "targets": [
        {"expr": "streaming_sessions_active", "legendFormat": "active"}
      ]
    },
    {
      "title": "RAG Confidence",
      "type": "graph",
      "targets": [
        {"expr": "avg(rag_confidence)", "legendFormat": "avg confidence"},
        {"expr": "histogram_quantile(0.95, rate(rag_confidence_bucket[5m]))", "legendFormat": "p95 confidence"}
      ]
    },
    {
      "title": "Retrieval Latency",
      "type": "graph",
      "targets": [
        {"expr": "histogram_quantile(0.95, sum(rate(retrieval_search_time_seconds_bucket[5m])) by (le))", "legendFormat": "p95"},
        {"expr": "histogram_quantile(0.50, sum(rate(retrieval_search_time_seconds_bucket[5m])) by (le))", "legendFormat": "p50"}
      ]
    }
  ]
}
```

### 2. AI/ML Dashboard

```json
{
  "title": "AI/ML Metrics",
  "panels": [
    {
      "title": "Embedding Generation Time",
      "type": "graph",
      "targets": [
        {"expr": "histogram_quantile(0.95, rate(ai_embedding_time_seconds_bucket[5m]))", "legendFormat": "p95"}
      ]
    },
    {
      "title": "Generation Time (Streaming vs Non)",
      "type": "graph",
      "targets": [
        {"expr": "histogram_quantile(0.95, rate(ai_generation_time_seconds{streaming=\"true\"}_bucket[5m]))", "legendFormat": "streaming p95"},
        {"expr": "histogram_quantile(0.95, rate(ai_generation_time_seconds{streaming=\"false\"}_bucket[5m]))", "legendFormat": "non-streaming p95"}
      ]
    },
    {
      "title": "Token Throughput",
      "type": "graph",
      "targets": [
        {"expr": "rate(ai_token_count_total{type=\"completion\"}[5m])", "legendFormat": "completion tokens/sec"},
        {"expr": "rate(ai_token_count_total{type=\"prompt\"}[5m])", "legendFormat": "prompt tokens/sec"}
      ]
    },
    {
      "title": "Ollama Memory",
      "type": "graph",
      "targets": [
        {"expr": "ollama_memory_usage / 1024 / 1024 / 1024", "legendFormat": "GB"}
      ]
    },
    {
      "title": "Models Loaded",
      "type": "stat",
      "targets": [
        {"expr": "ollama_models_loaded", "legendFormat": "loaded"}
      ]
    }
  ]
}
```

### 3. Retrieval Dashboard

```json
{
  "title": "Retrieval Pipeline",
  "panels": [
    {
      "title": "Search Type Distribution",
      "type": "piechart",
      "targets": [
        {"expr": "sum(increase(search_queries_total[1h])) by (type)", "legendFormat": "{{type}}"}
      ]
    },
    {
      "title": "Vector vs BM25 vs Hybrid Latency",
      "type": "graph",
      "targets": [
        {"expr": "histogram_quantile(0.95, rate(retrieval_search_time_seconds{type=\"vector\"}_bucket[5m]))", "legendFormat": "vector p95"},
        {"expr": "histogram_quantile(0.95, rate(retrieval_search_time_seconds{type=\"bm25\"}_bucket[5m]))", "legendFormat": "bm25 p95"},
        {"expr": "histogram_quantile(0.95, rate(retrieval_search_time_seconds{type=\"hybrid\"}_bucket[5m]))", "legendFormat": "hybrid p95"}
      ]
    },
    {
      "title": "Rerank Time",
      "type": "graph",
      "targets": [
        {"expr": "histogram_quantile(0.95, rate(retrieval_rerank_time_seconds_bucket[5m]))", "legendFormat": "p95"}
      ]
    },
    {
      "title": "RRF Fusion Time",
      "type": "graph",
      "targets": [
        {"expr": "histogram_quantile(0.95, rate(retrieval_rrf_time_seconds_bucket[5m]))", "legendFormat": "p95"}
      ]
    },
    {
      "title": "Results per Query",
      "type": "graph",
      "targets": [
        {"expr": "avg(retrieval_results_count)", "legendFormat": "avg"},
        {"expr": "histogram_quantile(0.95, rate(retrieval_results_count_bucket[5m]))", "legendFormat": "p95"}
      ]
    }
  ]
}
```

### 4. Infrastructure Dashboard

```json
{
  "title": "Infrastructure",
  "panels": [
    {
      "title": "CPU Usage",
      "type": "graph",
      "targets": [
        {"expr": "avg(cpu_usage_percent) by (pod)", "legendFormat": "{{pod}}"}
      ]
    },
    {
      "title": "Memory Usage",
      "type": "graph",
      "targets": [
        {"expr": "memory_usage_bytes / 1024 / 1024 / 1024", "legendFormat": "GB {{pod}}"}
      ]
    },
    {
      "title": "Database Connections",
      "type": "graph",
      "targets": [
        {"expr": "db_connections_active", "legendFormat": "active"},
        {"expr": "db_connections_idle", "legendFormat": "idle"}
      ]
    },
    {
      "title": "Disk Usage",
      "type": "gauge",
      "targets": [
        {"expr": "disk_usage_percent", "legendFormat": "%"}
      ]
    },
    {
      "title": "Network I/O",
      "type": "graph",
      "targets": [
        {"expr": "rate(network_receive_bytes_total[5m])", "legendFormat": "RX MB/s"},
        {"expr": "rate(network_transmit_bytes_total[5m])", "legendFormat": "TX MB/s"}
      ]
    }
  ]
}
```

---

## Alerting Rules

```yaml
# alerts.yaml
groups:
- name: kifpilot-alerts
  interval: 30s
  rules:
  # Critical
  - alert: ServiceDown
    expr: up{job="kifpilot-backend"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "KifPilot backend down"
      description: "Backend has been down for > 2 minutes"

  - alert: HighErrorRate
    expr: sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate (>5%)"
      description: "Error rate is {{ $value | humanizePercentage }}"

  - alert: HighLatency
    expr: histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le)) > 5
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

  - alert: ChromaDBDown
    expr: up{job="chromadb"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "ChromaDB down"

  - alert: PostgreSQLDown
    expr: pg_up == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "PostgreSQL down"

  # Warning
  - alert: HighMemoryUsage
    expr: (container_memory_usage_bytes / container_spec_memory_limit_bytes) > 0.9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Memory usage > 90% for {{ $labels.pod }}"

  - alert: HighCPUUsage
    expr: (rate(container_cpu_usage_seconds_total[5m]) / container_spec_cpu_quota/container_spec_cpu_period) > 0.85
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "CPU usage > 85% for {{ $labels.pod }}"

  - alert: DiskSpaceLow
    expr: (disk_free_bytes / disk_total_bytes) < 0.1
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Disk space < 10% on {{ $labels.instance }}"

  - alert: HighQueueDepth
    expr: redis_list_length{list="task_queue"} > 1000
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Task queue depth > 1000"

  - alert: StreamingStalled
    expr: time() - streaming_last_token_timestamp > 60
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: "Streaming stalled > 60s"

  - alert: HPAAtMaxReplicas
    expr: kube_horizontalpodautoscaler_status_desired_replicas == kube_horizontalpodautoscaler_spec_max_replicas
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "HPA at max replicas for {{ $labels.horizontalpodautoscaler }}"

  # Info
  - alert: NewDeployment
    expr: kube_deployment_status_replicas_available > 0
    for: 1m
    labels:
      severity: info
    annotations:
      summary: "New deployment detected: {{ $labels.deployment }}"
```

---

## Loki Log Aggregation

### Deployment

```yaml
# loki.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: loki-config
  namespace: monitoring
data:
  loki.yaml: |
    auth_enabled: false
    server:
      http_listen_port: 3100
    ingester:
      lifecycler:
        address: 127.0.0.1
        ring:
          kvstore:
            store: inmemory
          replication_factor: 1
        final_sleep: 0s
      chunk_idle_period: 5m
      chunk_retain_period: 30s
    schema_config:
      configs:
      - from: 2024-01-01
        store: boltdb-shipper
        object_store: filesystem
        schema: v11
        index:
          prefix: index_
          period: 24h
    storage_config:
      boltdb_shipper:
        active_index_directory: /loki/index
        cache_location: /loki/cache
        shared_store: filesystem
      filesystem:
        directory: /loki/chunks
    limits_config:
      reject_old_samples: true
      reject_old_samples_max_age: 168h
      ingestion_rate_mb: 50
      ingestion_burst_size_mb: 100
```

### Promtail Configuration

```yaml
# promtail.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: promtail-config
  namespace: monitoring
data:
  promtail.yaml: |
    server:
      http_listen_port: 9080
      grpc_listen_port: 0
    positions:
      filename: /tmp/positions.yaml
    clients:
    - url: http://loki:3100/loki/api/v1/push
    scrape_configs:
    - job_name: kifpilot
      static_configs:
      - targets:
        - localhost
        labels:
          job: kifpilot
          __path__: /var/log/kifpilot/*.log
      pipeline_stages:
      - json:
          expressions:
            request_id: request_id
            user_id: user_id
            organization_id: organization_id
            level: level
            message: message
      - labels:
          request_id:
          user_id:
          organization_id:
          level:
```

---

## Log Queries

### Useful LogQL Queries

```logql
# Errors in last hour
{job="kifpilot"} |= "error" | json | level = "error" | __line__ 

# Slow requests (>5s)
{job="kifpilot"} | json | process_time_ms > 5000

# Rate limit events
{job="kifpilot"} | json | event_type = "rate_limit_exceeded"

# Guardrails triggered
{job="kifpilot"} | json | guardrails_triggered = true

# Specific user activity
{job="kifpilot"} | json | user_id = "user-uuid-here"

# Specific request
{job="kifpilot"} | json | request_id = "request-uuid-here"

# RAG queries
{job="kifpilot"} | json | endpoint =~ "rag.*"

# Streaming events
{job="kifpilot"} | json | endpoint = "chat/stream"
```

---

## Tracing with Jaeger

### Deployment

```yaml
# jaeger.yaml
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: jaeger
  namespace: monitoring
spec:
  strategy: production
  collector:
    replicas: 2
    options:
      collector.zipkin.host-port: 9411
  query:
    replicas: 2
    options:
      query.base-path: /jaeger
  storage:
    type: elasticsearch
    elasticsearch:
      nodeCount: 3
      redundancyPolicy: SingleRedundancy
    esIndexCleaner:
      enabled: true
      numberOfDays: 14
      schedule: "55 23 * * *"
```

### Trace Context Propagation

```python
# Automatic instrumentation captures:
# - HTTP requests (method, path, status)
# - Database queries (SQL, duration)
# - External HTTP calls (Ollama, ChromaDB)
# - Custom spans for business logic

# Custom span example
@tracer.start_as_current_span("rag.generate_answer")
async def generate_answer(question: str, context: str):
    with tracer.start_as_current_span("retrieval") as span:
        span.set_attribute("question.length", len(question))
        results = await retrieval.search(question)
        span.set_attribute("results.count", len(results))
    
    with tracer.start_as_current_span("generation") as span:
        answer = await llm.generate(prompt)
        span.set_attribute("answer.length", len(answer))
    
    return answer
```

---

## Runbook Links

| Alert | Runbook |
|-------|---------|
| ServiceDown | [runbooks/service-down.md](runbooks/service-down.md) |
| HighErrorRate | [runbooks/high-error-rate.md](runbooks/high-error-rate.md) |
| HighLatency | [runbooks/high-latency.md](runbooks/high-latency.md) |
| OllamaDown | [runbooks/ollama-down.md](runbooks/ollama-down.md) |
| HighMemoryUsage | [runbooks/high-memory.md](runbooks/high-memory.md) |
| DiskSpaceLow | [runbooks/disk-space.md](runbooks/disk-space.md) |
| StreamingStalled | [runbooks/streaming-stalled.md](runbooks/streaming-stalled.md) |

---

## On-Call Procedures

### Escalation
1. **Tier 1**: On-call engineer (15 min response)
2. **Tier 2**: Team lead (30 min if no response)
3. **Tier 3**: Engineering manager (1 hour)

### Communication
- Slack: #incidents
- PagerDuty: Critical alerts
- Status page: status.example.com

### Post-Incident
- RCA within 48 hours
- Action items tracked in Jira
- Runbook updates