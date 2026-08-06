# Hybrid Search (BM25 + Vector + RRF)

## Overview

Hybrid search combines vector similarity (semantic) with BM25 (lexical) using Reciprocal Rank Fusion (RRF) for optimal retrieval quality.

## Why Hybrid Search?

| Search Type | Strengths | Weaknesses |
|-------------|-----------|------------|
| **Vector** | Semantic understanding, synonyms, concepts | Misses exact terms, numbers, codes |
| **BM25** | Exact term matching, rare terms, IDs/codes | No semantic understanding |
| **Hybrid** | Best of both worlds | More complex, needs tuning |

## BM25 Algorithm

```
score(D,Q) = Σ IDF(q) * (f(q,D) * (k1 + 1)) / (f(q,D) + k1 * (1 - b + b * |D|/avgdl))

Where:
- q = query term
- D = document
- f(q,D) = term frequency in document
- |D| = document length
- avgdl = average document length
- k1 = term saturation (typically 1.2-2.0)
- b = length normalization (typically 0.75)
- IDF(q) = log((N - n(q) + 0.5) / (n(q) + 0.5) + 1)
  - N = total documents
  - n(q) = documents containing term q
```

## RRF (Reciprocal Rank Fusion)

```
RRF_score(d) = Σ 1 / (k + rank_i(d))

Where:
- d = document
- rank_i(d) = rank of document in result list i (1-indexed)
- k = constant (typically 60)
- i = each result list (vector, bm25, etc.)

Properties:
- No score normalization needed
- Robust to different score scales
- Parameter k controls impact of high ranks
- k=60 is standard default
```

## Implementation

```python
# services/retrieval/search.py
class HybridSearchService:
    def __init__(
        self,
        vector_store: VectorStoreService,
        bm25_index: BM25Index,
        embedding_service: EmbeddingService,
        rrf_k: int = 60
    ):
        self.vector_store = vector_store
        self.bm25 = bm25_index
        self.embedding = embedding_service
        self.rrf_k = rrf_k
    
    async def search(
        self,
        query: str,
        org_id: str,
        kb_ids: List[str],
        top_k: int = 10,
        alpha: float = 0.5,
        use_rrf: bool = True,
        rrf_k: int = None,
        filters: dict = None
    ) -> List[HybridResult]:
        """
        Hybrid search with configurable fusion
        
        Args:
            query: Search query
            org_id: Organization ID
            kb_ids: Knowledge base IDs to search
            top_k: Final result count
            alpha: Weight for weighted fusion (vector weight)
            use_rrf: Use RRF vs weighted fusion
            rrf_k: RRF constant (default 60)
            filters: Metadata filters
        """
        rrf_k = rrf_k or self.rrf_k
        
        # 1. Generate query embedding
        query_vector = await self.embedding.generate_single(query)
        
        # 2. Vector search (get more candidates for fusion)
        vector_results = []
        for kb_id in kb_ids:
            collection = f"org_{org_id}_kb_{kb_id}"
            results = await self.vector_store.search(
                collection_name=collection,
                query_vector=query_vector,
                top_k=top_k * 3,  # Get extra for fusion
                filters=filters
            )
            for r in results:
                r.metadata["knowledge_base_id"] = kb_id
                r.source = "vector"
            vector_results.extend(results)
        
        # 3. BM25 search
        bm25_results = self.bm25.search(org_id, query, top_k * 3)
        for r in bm25_results:
            r.source = "bm25"
        
        # 4. Fuse results
        if use_rrf:
            fused = self._rrf_fusion(vector_results, bm25_results, rrf_k)
        else:
            fused = self._weighted_fusion(vector_results, bm25_results, alpha)
        
        # 5. Sort and return top_k
        fused.sort(key=lambda x: x.score, reverse=True)
        return fused[:top_k]
    
    def _rrf_fusion(
        self,
        vector_results: List[HybridResult],
        bm25_results: List[HybridResult],
        k: int
    ) -> List[HybridResult]:
        """Reciprocal Rank Fusion - no score normalization needed"""
        # Build rank maps
        vector_ranks = {r.id: i + 1 for i, r in enumerate(vector_results)}
        bm25_ranks = {r.id: i + 1 for i, r in enumerate(bm25_results)}
        
        all_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())
        fused = []
        
        for doc_id in all_ids:
            vr = vector_ranks.get(doc_id, len(vector_results) + 1)
            br = bm25_ranks.get(doc_id, len(bm25_results) + 1)
            
            # RRF formula
            rrf_score = 1.0 / (k + vr) + 1.0 / (k + br)
            
            # Get metadata from either source
            orig = next((r for r in vector_results if r.id == doc_id), None)
            if not orig:
                orig = next((r for r in bm25_results if r.id == doc_id), None)
            
            if orig:
                fused.append(HybridResult(
                    id=doc_id,
                    text=orig.text,
                    metadata=orig.metadata,
                    score=rrf_score,
                    source="rrf",
                    vector_rank=vr,
                    bm25_rank=br
                ))
        
        fused.sort(key=lambda x: x.score, reverse=True)
        return fused
    
    def _weighted_fusion(
        self,
        vector_results: List[HybridResult],
        bm25_results: List[HybridResult],
        alpha: float
    ) -> List[HybridResult]:
        """Weighted score fusion with min-max normalization"""
        # Normalize scores to [0,1]
        def normalize(results):
            if not results:
                return {}
            scores = [r.score for r in results]
            min_s, max_s = min(scores), max(scores)
            if max_s == min_s:
                return {r.id: 1.0 for r in results}
            return {r.id: (r.score - min_s) / (max_s - min_s) for r in results}
        
        v_norm = normalize(vector_results)
        b_norm = normalize(bm25_results)
        
        all_ids = set(v_norm.keys()) | set(b_norm.keys())
        fused = []
        
        for doc_id in all_ids:
            vs = v_norm.get(doc_id, 0)
            bs = b_norm.get(doc_id, 0)
            fused_score = alpha * vs + (1 - alpha) * bs
            
            orig = next((r for r in vector_results if r.id == doc_id), None)
            if not orig:
                orig = next((r for r in bm25_results if r.id == doc_id), None)
            
            if orig:
                fused.append(HybridResult(
                    id=doc_id,
                    text=orig.text,
                    metadata=orig.metadata,
                    score=fused_score,
                    source="weighted",
                    vector_score=vs,
                    bm25_score=bs
                ))
        
        fused.sort(key=lambda x: x.score, reverse=True)
        return fused
```

## BM25 Index Implementation

```python
# services/retrieval/bm25.py
class BM25Index:
    def __init__(self, persist_path: str = "./bm25_index", k1: float = 1.5, b: float = 0.75):
        self.persist_path = Path(persist_path)
        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.k1 = k1
        self.b = b
        
        self.indices: Dict[str, BM25Okapi] = {}
        self.doc_mapping: Dict[str, List[str]] = {}  # org_id -> [doc_ids]
        self.doc_lengths: Dict[str, List[int]] = {}
        self.avgdl: Dict[str, float] = {}
        self.tokenizer = self._default_tokenizer
    
    def _default_tokenizer(self, text: str) -> List[str]:
        import re
        return re.findall(r'\b\w+\b', text.lower())
    
    def add_documents(self, org_id: str, documents: List[DocumentChunk]):
        """Add documents to BM25 index for organization"""
        if org_id not in self.indices:
            self.indices[org_id] = BM25Okapi([], tokenizer=self.tokenizer)
            self.doc_mapping[org_id] = []
            self.doc_lengths[org_id] = []
        
        # Tokenize all documents
        tokenized = [self.tokenizer(d.text) for d in documents]
        
        # Update index
        self.indices[org_id].add_documents(tokenized)
        
        # Track mappings
        for d in documents:
            self.doc_mapping[org_id].append(d.id)
            self.doc_lengths[org_id].append(len(d.text))
        
        # Recalculate avgdl
        self.avgdl[org_id] = sum(self.doc_lengths[org_id]) / len(self.doc_lengths[org_id])
        
        # Persist
        self._persist(org_id)
    
    def search(self, org_id: str, query: str, top_k: int = 10) -> List[BM25Result]:
        if org_id not in self.indices:
            return []
        
        tokenized_query = self.tokenizer(query)
        scores = self.indices[org_id].get_scores(tokenized_query)
        
        # Get top-k indices
        top_indices = np.argsort(scores)[::-1][:top_k]
        
        return [
            BM25Result(
                document_id=self.doc_mapping[org_id][idx],
                score=float(scores[idx]),
                rank=i + 1
            )
            for i, idx in enumerate(top_indices)
            if scores[idx] > 0
        ]
    
    def _persist(self, org_id: str):
        """Persist index to disk"""
        import pickle
        self.persist_path.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path / f"bm25_{org_id}.pkl", "wb") as f:
            pickle.dump({
                "index": self.indices[org_id],
                "doc_mapping": self.doc_mapping[org_id],
                "doc_lengths": self.doc_lengths[org_id],
                "avgdl": self.avgdl[org_id]
            }, f)
    
    def load(self, org_id: str) -> bool:
        """Load index from disk"""
        import pickle
        path = self.persist_path / f"bm25_{org_id}.pkl"
        if not path.exists():
            return False
        
        with open(path, "rb") as f:
            data = pickle.load(f)
            self.indices[org_id] = data["index"]
            self.doc_mapping[org_id] = data["doc_mapping"]
            self.doc_lengths[org_id] = data["doc_lengths"]
            self.avgdl[org_id] = data["avgdl"]
        return True
```

## Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # Hybrid Search
    HYBRID_RRF_K: int = 60
    HYBRID_DEFAULT_ALPHA: float = 0.5
    HYBRID_USE_RRF: bool = True
    
    # BM25
    BM25_K1: float = 1.5
    BM25_B: float = 0.75
    BM25_PERSIST_DIR: str = "./bm25_index"
    
    # Candidate multiplication for fusion
    HYBRID_CANDIDATE_MULTIPLIER: int = 3
```

## API Usage

```python
# presentation/api/v1/routes/retrieval.py
@router.post("/hybrid-search")
async def hybrid_search(
    request: HybridSearchRequest,
    org_id: str = Depends(get_current_organization_id),
    service: RetrievalService = Depends(get_retrieval_service)
):
    return await service.hybrid_search(
        query=request.query,
        org_id=org_id,
        kb_ids=request.kb_ids or await get_user_kb_ids(org_id),
        top_k=request.top_k,
        alpha=request.alpha,
        use_rrf=request.use_rrf,
        rrf_k=request.rrf_k,
        minimum_score=request.minimum_score,
        filters=request.filters
    )

# Request model
class HybridSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    minimum_score: float = 0.3
    kb_ids: Optional[List[str]] = None
    alpha: float = Field(0.5, ge=0, le=1)
    use_rrf: bool = True
    rrf_k: int = 60
    filters: Optional[dict] = None
```

## Tuning Guidelines

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `rrf_k` | 60 | 10-100 | Lower = more weight to top ranks |
| `alpha` | 0.5 | 0-1 | Vector weight in weighted fusion |
| `candidate_multiplier` | 3 | 2-5 | Extra candidates for fusion |
| `bm25_k1` | 1.5 | 1.2-2.0 | Term saturation |
| `bm25_b` | 0.75 | 0-1 | Length normalization |

## When to Use Each

| Scenario | Recommended |
|----------|-------------|
| General purpose | RRF (default) |
| Known exact terms important | Weighted (alpha=0.3-0.5) |
| Semantic queries | RRF or alpha=0.7 |
| Technical codes/IDs | Weighted (alpha=0.2) |
| Mixed workload | RRF |

## Monitoring

```python
# Metrics
hybrid_search_time = Histogram("hybrid_search_seconds", "Hybrid search time")
rrf_fusion_time = Histogram("rrf_fusion_seconds", "RRF fusion time")
weighted_fusion_time = Histogram("weighted_fusion_seconds", "Weighted fusion time")
hybrid_vector_ratio = Gauge("hybrid_vector_ratio", "Vector results / total")
hybrid_bm25_ratio = Gauge("hybrid_bm25_ratio", "BM25 results / total")
hybrid_fusion_method = Counter("hybrid_fusion_method", "Fusion method used", ["method"])
```