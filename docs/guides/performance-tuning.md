# Performance Tuning Guide

## Overview

Optimization strategies for latency, throughput, and resource utilization.

## Performance Targets

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| API p95 latency | < 500ms | > 1s | > 5s |
| RAG p95 latency | < 3s | > 5s | > 10s |
| Streaming TTFT | < 500ms | > 1s | > 2s |
| Retrieval p95 | < 200ms | > 500ms | > 1s |
| Error rate | < 0.1% | > 1% | > 5% |
| CPU usage | < 70% | > 80% | > 90% |
| Memory usage | < 75% | > 85% | > 95% |

---

## Backend Optimization

### 1. Database Optimization

#### Connection Pooling
```python
# config.py
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 10
DATABASE_POOL_TIMEOUT = 30
DATABASE_POOL_RECYCLE = 3600
```

#### Indexing Strategy
```sql
-- Critical indexes for common queries
CREATE INDEX idx_documents_org_status ON documents(organization_id, status);
CREATE INDEX idx_documents_org_created ON documents(organization_id, created_at DESC);
CREATE INDEX idx_chunks_doc_idx ON document_chunks(document_id, chunk_index);
CREATE INDEX idx_conversations_user ON conversations(user_id, updated_at DESC);
CREATE INDEX idx_messages_conv ON conversation_messages(conversation_id, created_at);
CREATE INDEX idx_user_roles_user_org ON user_roles(user_id, organization_id);
```

#### Query Optimization
```python
# Use select_related / joinedload to avoid N+1
async def get_conversation_with_messages(conv_id: str):
    stmt = (
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conv_id)
    )
    return await session.execute(stmt)

# Use pagination for large lists
async def list_documents(org_id: str, page: int, page_size: int):
    offset = (page - 1) * page_size
    stmt = (
        select(Document)
        .where(Document.organization_id == org_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
```

### 2. Vector Store Optimization

#### ChromaDB Configuration
```yaml
# ChromaDB settings for production
chromadb:
  hnsw:
    space: "cosine"
    construction_ef: 200
    search_ef: 100
    M: 16
  persistence:
    path: "/data/chroma"
  performance:
    num_threads: 4
```

#### Collection Management
```python
# One collection per KB per org for isolation
collection_name = f"org_{org_id}_kb_{kb_id}"

# Batch operations for bulk inserts
async def add_documents_batch(collection, documents: List[VectorDoc], batch_size: int = 1000):
    for i in range(0, len(documents), batch_size):
        batch = documents[i:i + batch_size]
        await collection.add(
            ids=[d.id for d in batch],
            embeddings=[d.embedding for d in batch],
            metadatas=[d.metadata for d in batch],
            documents=[d.text for d in batch]
        )
```

### 3. LLM/Ollama Optimization

#### Model Selection
| Use Case | Model | Quantization | VRAM |
|----------|-------|--------------|------|
| Best quality | qwen3.5:4b | q8_0 | ~8GB |
| Balanced | qwen3.5:4b | q4_K_M | ~4GB |
| Fast | qwen2.5:1.5b | q4_K_M | ~2GB |
| Embeddings | nomic-embed-text | q8_0 | ~1GB |

#### Ollama Configuration
```yaml
# ollama config
OLLAMA_NUM_PARALLEL: 2
OLLAMA_MAX_LOADED_MODELS: 2
OLLAMA_FLASH_ATTENTION: true
OLLAMA_KV_CACHE_TYPE: "fp16"
```

#### Generation Settings
```python
# Optimal settings for RAG
generation_options = {
    "temperature": 0.1,      # Low for factual
    "top_p": 0.9,           # Nucleus sampling
    "top_k": 40,            # Limit vocabulary
    "repeat_penalty": 1.1,  # Reduce repetition
    "max_tokens": 2048,     # Limit response length
    "stop": ["\n\n\n"],     # Stop at paragraph breaks
}
```

### 4. Retrieval Pipeline Optimization

#### Parallel Search
```python
async def hybrid_search_parallel(query: str, kb_ids: List[str]):
    # Run vector and BM25 in parallel
    vector_task = asyncio.create_task(vector_search(query, kb_ids))
    bm25_task = asyncio.create_task(bm25_search(query))
    
    vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
    return rrf_fusion(vector_results, bm25_results)
```

#### Candidate Filtering
```python
# Get extra candidates for fusion, then trim
CANDIDATE_MULTIPLIER = 3

async def search_with_fusion(query, top_k=10):
    candidates = top_k * CANDIDATE_MULTIPLIER
    vector_results = await vector_search(query, top_k=candidates)
    bm25_results = await bm25_search(query, top_k=candidates)
    fused = rrf_fusion(vector_results, bm25_results)
    return fused[:top_k]
```

#### Reranking Optimization
```python
# Limit rerank candidates
RERANK_MAX_CANDIDATES = 20  # Reduce from 50
RERANK_BATCH_SIZE = 16      # Optimal for GPU

async def rerank(query, documents, top_k=5):
    candidates = documents[:RERANK_MAX_CANDIDATES]
    pairs = [(query, d.text) for d in candidates]
    
    # Batch inference
    scores = []
    for i in range(0, len(pairs), RERANK_BATCH_SIZE):
        batch = pairs[i:i+RERANK_BATCH_SIZE]
        batch_scores = await reranker.score_batch(batch)
        scores.extend(batch_scores)
    
    return sort_by_score(documents, scores)[:top_k]
```

### 5. Caching Strategy

#### Redis Caching
```python
# Cache embeddings for repeated queries
async def get_cached_embedding(query: str) -> Optional[List[float]]:
    key = f"emb:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    return None

async def cache_embedding(query: str, embedding: List[float]):
    key = f"emb:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
    await redis.setex(key, 3600, json.dumps(embedding))

# Cache RAG responses for identical queries
async def get_cached_rag_response(query: str, kb_ids: List[str]) -> Optional[RAGResponse]:
    key = f"rag:{hashlib.sha256(f'{query}:{sorted(kb_ids)}'.encode()).hexdigest()[:16]}"
    cached = await redis.get(key)
    if cached:
        return RAGResponse.parse_raw(cached)
    return None
```

#### Query Expansion Caching
```python
# Cache expanded queries
EXPANSION_CACHE_TTL = 3600

async def get_expansions(query: str) -> List[str]:
    key = f"exp:{hashlib.sha256(query.encode()).hexdigest()[:16]}"
    cached = await redis.get(key)
    if cached:
        return json.loads(cached)
    
    expansions = await llm_expand(query)
    await redis.setex(key, EXPANSION_CACHE_TTL, json.dumps(expansions))
    return expansions
```

### 6. Concurrency Control

#### Semaphore for External APIs
```python
# Limit concurrent Ollama requests
OLLAMA_SEMAPHORE = asyncio.Semaphore(4)

async def safe_ollama_generate(prompt: str):
    async with OLLAMA_SEMAPHORE:
        return await ollama.generate(prompt)
```

#### Connection Pooling
```python
# HTTP client pooling
httpx_client = httpx.AsyncClient(
    limits=httpx.Limits(
        max_connections=100,
        max_keepalive_connections=20
    ),
    timeout=30.0
)
```

---

## Frontend Optimization

### 1. Bundle Optimization

```javascript
// vite.config.ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
          charts: ['recharts'],
        }
      }
    },
    cssCodeSplit: true,
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true,
        drop_debugger: true
      }
    }
  }
})
```

### 2. Code Splitting

```tsx
// Lazy load feature pages
const DocumentsPage = lazy(() => import('./features/documents/DocumentsPage'));
const KnowledgeBasePage = lazy(() => import('./features/knowledge-base/KnowledgeBasePage'));
const ChatPage = lazy(() => import('./features/chat/ChatPage'));
const AdminDashboardPage = lazy(() => import('./features/admin/AdminDashboardPage'));

// Suspense boundary
<Suspense fallback={<PageLoader />}>
  <Routes>...</Routes>
</Suspense>
```

### 3. Virtualization for Large Lists

```tsx
import { FixedSizeList as List } from 'react-window';

function DocumentTable({ documents }) {
  const Row = ({ index, style }) => (
    <div style={style}>
      <DocumentRow document={documents[index]} />
    </div>
  );

  return (
    <List
      height={600}
      itemCount={documents.length}
      itemSize={50}
      width="100%"
    >
      {Row}
    </List>
  );
}
```

### 4. Memoization

```tsx
// Prevent unnecessary re-renders
const DocumentRow = memo(({ document, onDelete }) => (
  <tr>...</tr>
));

// Virtualized chat messages
const ChatMessage = memo(({ message }) => (
  <div>...</div>
));
```

---

## Infrastructure Optimization

### 1. Kubernetes Resources

```yaml
# Production resource limits
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "2000m"
    memory: "4Gi"
```

### 2. HPA Configuration

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: kifpilot-backend-hpa
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
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
    scaleUp:
      stabilizationWindowSeconds: 0
```

### 3. Node Affinity for GPU Workloads

```yaml
affinity:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: nvidia.com/gpu
          operator: Exists
```

---

## Monitoring Performance

### Key Dashboards

1. **API Latency**: p50, p95, p99 by endpoint
2. **RAG Pipeline**: Retrieval time, generation time, total
3. **GPU Utilization**: Ollama memory, compute
4. **Database**: Connections, query time, locks
5. **Cache Hit Rate**: Redis hit/miss ratio

### Profiling Commands

```bash
# Python profiling
python -m cProfile -o profile.stats -m app.main

# Analyze
python -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"

# Memory profiling
python -m memory_profiler app/main.py

# SQL query analysis
EXPLAIN ANALYZE SELECT * FROM documents WHERE organization_id = '...';
```

---

## Load Testing

### k6 Script

```javascript
// load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 10 },
    { duration: '5m', target: 50 },
    { duration: '2m', target: 100 },
    { duration: '5m', target: 100 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'],
    http_req_failed: ['rate<0.01'],
  },
};

export default function () {
  const token = __ENV.TOKEN;
  
  // Health check
  http.get('http://api.example.com/health');
  
  // Search
  http.post('http://api.example.com/api/v1/retrieval/search', 
    JSON.stringify({ query: 'test query', top_k: 5 }),
    { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } }
  );
  
  // RAG query
  http.post('http://api.example.com/api/v1/rag/query',
    JSON.stringify({ question: 'What is the refund policy?', top_k: 5 }),
    { headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' } }
  );
  
  sleep(1);
}
```

### Run Load Test

```bash
k6 run -e TOKEN=$TOKEN load-test.js
```

---

## Optimization Checklist

- [ ] Database indexes created
- [ ] Connection pooling configured
- [ ] ChromaDB HNSW tuned
- [ ] Ollama using GPU with quantization
- [ ] Parallel retrieval enabled
- [ ] Reranking candidates limited
- [ ] Redis caching for embeddings/responses
- [ ] Semaphores for external APIs
- [ ] HPA configured for all services
- [ ] Frontend code splitting
- [ ] Bundle size < 500KB gzipped
- [ ] Load testing completed
- [ ] Monitoring alerts configured