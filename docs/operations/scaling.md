# Scaling Guide

## Overview

Horizontal and vertical scaling strategies for each component.

## Scaling Targets

| Component | Metric | Scale Up | Scale Down |
|-----------|--------|----------|------------|
| Backend API | CPU > 70% | +2 pods | -1 pod (5min) |
| Backend API | Memory > 80% | +2 pods | -1 pod (5min) |
| Backend API | RPS > 100/pod | +3 pods | -1 pod (10min) |
| Frontend | CPU > 70% | +2 pods | -1 pod (5min) |
| Workers | Queue depth > 50 | +2 pods | -1 pod (5min) |
| PostgreSQL | Connections > 80% | Read replica | - |
| ChromaDB | Query latency > 500ms | +1 node | - |
| Ollama | GPU memory > 85% | +1 GPU node | - |
| Redis | Memory > 80% | +1 shard | - |

---

## Backend API Scaling

### Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kifpilot-backend-hpa
  namespace: kifpilot
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kifpilot-backend
  minReplicas: 3
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Min
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
      - type: Pods
        value: 4
        periodSeconds: 15
      selectPolicy: Max
```

### Custom Metrics Adapter

```yaml
# Prometheus adapter for custom metrics
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-adapter-config
  namespace: monitoring
data:
  config.yaml: |
    rules:
    - seriesQuery: 'http_requests_total{namespace!="",pod!=""}'
      resources:
        overrides:
          namespace:
            resource: namespace
          pod:
            resource: pod
      name:
        matches: "^(.*)_total"
        as: "${1}_per_second"
      metricsQuery: 'sum(rate(<<.Series>>{<<.LabelMatchers>>}[2m])) by (<<.GroupBy>>)'
```

### Resource Requests/Limits

```yaml
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"
```

### Connection Pooling

```python
# Database connection pool
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600

# HTTP client pool
httpx_limits = httpx.Limits(
    max_connections=100,
    max_keepalive_connections=20,
    keepalive_expiry=30.0
)
```

---

## Frontend Scaling

### Static Asset Optimization

```nginx
# nginx.conf for frontend
server {
    location / {
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }
    
    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;
```

### CDN Configuration

```yaml
# CloudFront/Cloudflare settings
- Cache TTL: 1 year for static assets
- Cache TTL: 5 min for HTML
- Compression: Brotli + Gzip
- Edge locations: Global
- Origin: S3 + CloudFront / Cloudflare Pages
```

### HPA for Frontend

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kifpilot-frontend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: kifpilot-frontend
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

---

## Worker Scaling

### Queue-Based Scaling

```python
# Worker deployment with KEDA
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: kifpilot-worker-scaled
  namespace: kifpilot
spec:
  scaleTargetRef:
    name: kifpilot-worker
  pollingInterval: 15
  cooldownPeriod: 300
  minReplicaCount: 1
  maxReplicaCount: 10
  triggers:
  - type: redis
    metadata:
      address: redis://redis:6379
      listName: task_queue
      listLength: "50"
  - type: cpu
    metadata:
      type: Utilization
      value: "70"
```

### Worker Types

| Worker Type | Queue | Concurrency | Resources |
|-------------|-------|-------------|-----------|
| Document Processor | document_processing | 4 | CPU: 2, Mem: 4GB |
| Embedding Generator | embedding_generation | 2 | GPU: 1, Mem: 8GB |
| Index Updater | index_updates | 4 | CPU: 1, Mem: 2GB |
| Notification Sender | notifications | 10 | CPU: 0.5, Mem: 1GB |

---

## Database Scaling

### Read Replicas

```yaml
# PostgreSQL with read replicas
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: kifpilot-postgres
spec:
  instances: 3
  primary:
    resources:
      requests:
        memory: "2Gi"
        cpu: "1000m"
      limits:
        memory: "4Gi"
        cpu: "2000m"
  replication:
    slots:
      high_availability: 1
  bootstrap:
    recovery:
      source: backup-object
```

### Connection Pooling (PgBouncer)

```yaml
# PgBouncer deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
spec:
  replicas: 3
  template:
    spec:
      containers:
      - name: pgbouncer
        image: edoburu/pgbouncer:1.18
        env:
        - name: DATABASE_URL
          value: "postgresql://postgres:password@postgres:5432/kifpilot"
        - name: POOL_MODE
          value: "transaction"
        - name: MAX_CLIENT_CONN
          value: "1000"
        - name: DEFAULT_POOL_SIZE
          value: "25"
        ports:
        - containerPort: 6432
```

### Read/Write Split

```python
# Application-level routing
class DatabaseRouter:
    def __init__(self):
        self.primary = create_engine(PRIMARY_URL, pool_size=20)
        self.replica = create_engine(REPLICA_URL, pool_size=50)
    
    def get_session(self, read_only: bool = False):
        if read_only:
            return self.replica
        return self.primary

# Usage
async def list_documents(org_id: str):
    # Read operation - use replica
    async with db_router.get_session(read_only=True) as session:
        return await session.execute(select(Document).where(...))

async def create_document(data: dict):
    # Write operation - use primary
    async with db_router.get_session(read_only=False) as session:
        return await session.execute(insert(Document).values(...))
```

---

## Vector Store Scaling

### ChromaDB Cluster

```yaml
# ChromaDB cluster mode
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: chromadb
spec:
  serviceName: chromadb
  replicas: 3
  template:
    spec:
      containers:
      - name: chromadb
        image: chromadb/chroma:0.4.22
        env:
        - name: CHROMA_SERVER_HOST
          value: "0.0.0.0"
        - name: CHROMA_SERVER_HTTP_PORT
          value: "8000"
        - name: CHROMA_PERSIST_DIRECTORY
          value: "/data"
        - name: CHROMA_SERVER_AUTH_PROVIDER
          value: "chromadb.auth.basic_authn.BasicAuthnProvider"
        - name: CHROMA_SERVER_AUTH_CREDENTIALS_PROVIDER
          value: "chromadb.auth.basic_authn.BasicAuthnCredentialsProvider"
        - name: CHROMA_SERVER_CORS_ALLOW_ORIGINS
          value: '["*"]'
        volumeMounts:
        - name: data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 500Gi
```

### Collection Sharding

```python
# Shard by organization for isolation + performance
def get_collection_name(org_id: str, kb_id: str) -> str:
    # Hash org_id for shard distribution
    shard = hashlib.md5(org_id.encode()).hexdigest()[:2]
    return f"shard_{shard}_org_{org_id}_kb_{kb_id}"

# Query routing
async def search(query: str, org_id: str, kb_ids: List[str]):
    # Determine shards
    shards = {hashlib.md5(org_id.encode()).hexdigest()[:2] for org_id in org_ids}
    
    # Query each shard in parallel
    tasks = [search_shard(shard, query) for shard in shards]
    results = await asyncio.gather(*tasks)
    
    # Merge and rank
    return merge_results(results)
```

---

## Ollama Scaling

### GPU Node Pool

```yaml
# GPU node pool for Ollama
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: gpu-pool
spec:
  template:
    spec:
      nodeSelector:
        nvidia.com/gpu: "true"
      requirements:
      - key: "karpenter.sh/capacity-type"
        operator: In
        values: ["on-demand"]
      - key: "nvidia.com/gpu"
        operator: In
        values: ["1", "2", "4", "8"]
      - key: "kubernetes.io/arch"
        operator: In
        values: ["amd64"]
      limits:
        cpu: "16"
        memory: "64Gi"
        nvidia.com/gpu: "4"
```

### Model Parallelism

```python
# Multi-GPU model loading
OLLAMA_NUM_PARALLEL = 2  # Per GPU
OLLAMA_MAX_LOADED_MODELS = 2  # Per GPU

# For large models, use tensor parallelism
# ollama run --gpu-layers 999 qwen3.5:4b
```

### Request Queue

```python
# Semaphore-based concurrency control
class OllamaQueue:
    def __init__(self, max_concurrent: int = 8):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.request_queue: asyncio.Queue = asyncio.Queue()
    
    async def generate(self, prompt: str) -> AsyncGenerator[str, None]:
        async with self.semaphore:
            async for token in ollama_client.stream_generate(prompt):
                yield token
```

---

## Redis Scaling

### Cluster Mode

```yaml
# Redis Cluster
apiVersion: redis.opstreelabs.in/v1beta1
kind: RedisCluster
metadata:
  name: kifpilot-redis
spec:
  clusterSize: 6
  replicasPerMaster: 1
  resources:
    requests:
      memory: "2Gi"
      cpu: "500m"
    limits:
      memory: "4Gi"
      cpu: "1000m"
  persistence:
    enabled: true
    storageClass: "fast-ssd"
    size: 50Gi
```

### Sharding Strategy

```python
# Key sharding for multi-tenant
def get_redis_key(org_id: str, key_type: str, identifier: str) -> str:
    # Hash org_id for shard distribution
    shard = hashlib.md5(org_id.encode()).hexdigest()[:2]
    return f"shard:{shard}:org:{org_id}:{key_type}:{identifier}"

# Connection pooling per shard
redis_pools = {
    shard: ConnectionPool.from_url(f"redis://redis-{shard}:6379")
    for shard in SHARDS
}
```

---

## Monitoring Scaling Events

```yaml
# Prometheus alerts for scaling
groups:
- name: scaling-alerts
  rules:
  - alert: HPAReplicasAtMax
    expr: kube_horizontalpodautoscaler_status_desired_replicas == kube_horizontalpodautoscaler_spec_max_replicas
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "HPA at max replicas for {{ $labels.namespace }}/{{ $labels.horizontalpodautoscaler }}"
      
  - alert: HPAScaleDownStalled
    expr: kube_horizontalpodautoscaler_status_desired_replicas < kube_horizontalpodautoscaler_status_current_replicas
    for: 30m
    labels:
      severity: info
    annotations:
      summary: "HPA scale down stalled"
      
  - alert: PodsPending
    expr: kube_pod_status_phase{phase="Pending"} > 0
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "Pods stuck in Pending state"
```

---

## Cost Optimization

### Spot Instances for Workers

```yaml
# Worker node pool with spot instances
apiVersion: karpenter.sh/v1beta1
kind: NodePool
metadata:
  name: worker-spot-pool
spec:
  template:
    spec:
      requirements:
      - key: "karpenter.sh/capacity-type"
        operator: In
        values: ["spot"]
      - key: "karpenter.k8s.aws/instance-category"
        operator: In
        values: ["c", "m", "r"]
      limits:
        cpu: "8"
        memory: "32Gi"
      tolerations:
      - key: "spot-instance"
        operator: "Exists"
        effect: "NoSchedule"
```

### Right-Sizing

```bash
# Analyze resource usage
kubectl top pods -n kifpilot --sort-by=memory --no-headers | head -20

# Adjust requests/limits based on actual usage
# Target: 70-80% utilization of requests
```