# Retrieval Pipeline

## Overview

Multi-stage retrieval combining vector similarity, BM25 lexical search, RRF fusion, cross-encoder reranking, and context compression.

## Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RETRIEVAL PIPELINE                                │
│                                                                             │
│  Query ──▶ Expansion ──▶ Hybrid Search ──▶ Rerank ──▶ Compress ──▶ Context │
│    │          │            │              │         │           │           │
│    ▼          ▼            ▼              ▼         ▼           ▼           │
│ ┌──────┐  ┌────────┐  ┌───────────┐  ┌─────────┐ ┌─────────┐ ┌──────────┐  │
│ │Guard │  │ Rule/  │  │ Vector +  │  │ Cross-  │ │ Token   │ │ Assemble │  │
│ │rails │  │  LLM   │  │  BM25 +   │  │ Encoder │ │ Budget  │ │ + Cite   │  │
│ │      │  │ Expand │  │   RRF     │  │ (ms-    │ │ (8k)    │ │          │  │
│ └──────┘  └────────┘  └───────────┘  │  marco) │ └─────────┘ └──────────┘  │
│                                      └─────────┘                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Retrieval Service

```python
# services/retrieval/service.py
class RetrievalService:
    def __init__(
        self,
        vector_store: VectorStoreService,
        bm25_index: BM25Index,
        reranker: RerankerService,
        query_expander: QueryExpansionService,
        context_compressor: ContextCompressionService,
        settings: Settings
    ):
        self.vector_store = vector_store
        self.bm25 = bm25_index
        self.reranker = reranker
        self.expander = query_expander
        self.compressor = context_compressor
        self.settings = settings
    
    async def search(
        self,
        query: str,
        org_id: str,
        kb_ids: List[str],
        top_k: int = 10,
        minimum_score: float = 0.3,
        filters: dict = None
    ) -> RetrievalResponse:
        """Main search entry point - vector only"""
        start = time.perf_counter()
        
        # 1. Vector search across KBs
        all_results = []
        for kb_id in kb_ids:
            collection_name = f"org_{org_id}_kb_{kb_id}"
            results = await self.vector_store.search(
                collection_name=collection_name,
                query_vector=await self.embed_query(query),
                top_k=top_k * 2,
                filters=filters
            )
            for r in results:
                r.metadata["knowledge_base_id"] = kb_id
            all_results.extend(results)
        
        # 2. Sort by score, apply threshold
        all_results.sort(key=lambda x: x.score, reverse=True)
        filtered = [r for r in all_results if r.score >= minimum_score]
        
        return RetrievalResponse(
            results=filtered[:top_k],
            total_found=len(filtered),
            search_time_ms=(time.perf_counter() - start) * 1000
        )
    
    async def hybrid_search(
        self,
        query: str,
        org_id: str,
        kb_ids: List[str],
        top_k: int = 10,
        alpha: float = 0.5,
        use_rrf: bool = True,
        rrf_k: int = 60,
        minimum_score: float = 0.3,
        filters: dict = None
    ) -> RetrievalResponse:
        """Hybrid search: Vector + BM25 + RRF"""
        start = time.perf_counter()
        
        # 1. Vector search
        vector_results = []
        for kb_id in kb_ids:
            collection_name = f"org_{org_id}_kb_{kb_id}"
            results = await self.vector_store.search(
                collection_name=collection_name,
                query_vector=await self.embed_query(query),
                top_k=top_k * 3,
                filters=filters
            )
            for r in results:
                r.metadata["knowledge_base_id"] = kb_id
                r.source = "vector"
            vector_results.extend(results)
        
        # 2. BM25 search
        bm25_results = self.bm25.search(org_id, query, top_k * 3)
        for r in bm25_results:
            r.metadata["knowledge_base_id"] = r.metadata.get("kb_id")
            r.source = "bm25"
        
        # 3. Fuse results
        if use_rrf:
            fused = self._rrf_fusion(vector_results, bm25_results, rrf_k)
        else:
            fused = self._weighted_fusion(vector_results, bm25_results, alpha)
        
        # 4. Apply score threshold
        filtered = [r for r in fused if r.score >= minimum_score]
        filtered.sort(key=lambda x: x.score, reverse=True)
        
        return RetrievalResponse(
            results=filtered[:top_k],
            total_found=len(filtered),
            search_time_ms=(time.perf_counter() - start) * 1000
        )
    
    async def rerank(
        self,
        query: str,
        documents: List[RetrievalResult],
        top_k: int = 5
    ) -> List[RetrievalResult]:
        """Cross-encoder reranking"""
        if not self.settings.RERANKER_ENABLED or not documents:
            return documents[:top_k]
        
        # Prepare pairs for reranker
        pairs = [(query, doc.text) for doc in documents]
        
        # Get rerank scores
        scores = await self.reranker.score(pairs)
        
        # Update scores and sort
        for doc, score in zip(documents, scores):
            doc.rerank_score = score
            doc.score = score  # Replace with rerank score
        
        documents.sort(key=lambda x: x.rerank_score or 0, reverse=True)
        return documents[:top_k]
    
    def _rrf_fusion(
        self,
        vector_results: List[RetrievalResult],
        bm25_results: List[RetrievalResult],
        k: int = 60
    ) -> List[RetrievalResult]:
        """Reciprocal Rank Fusion"""
        # Create ranking maps
        vector_ranks = {r.id: i + 1 for i, r in enumerate(vector_results)}
        bm25_ranks = {r.id: i + 1 for i, r in enumerate(bm25_results)}
        
        all_ids = set(vector_ranks.keys()) | set(bm25_ranks.keys())
        fused = []
        
        for doc_id in all_ids:
            vr = vector_ranks.get(doc_id, len(vector_results) + 1)
            br = bm25_ranks.get(doc_id, len(bm25_results) + 1)
            
            rrf_score = 1.0 / (k + vr) + 1.0 / (k + br)
            
            # Get original result for metadata
            orig = next((r for r in vector_results if r.id == doc_id), None)
            if not orig:
                orig = next((r for r in bm25_results if r.id == doc_id), None)
            
            if orig:
                fused.append(RetrievalResult(
                    id=doc_id,
                    text=orig.text,
                    metadata=orig.metadata,
                    score=rrf_score,
                    source="rrf_fusion",
                    vector_rank=vr,
                    bm25_rank=br
                ))
        
        fused.sort(key=lambda x: x.score, reverse=True)
        return fused
    
    def _weighted_fusion(
        self,
        vector_results: List[RetrievalResult],
        bm25_results: List[RetrievalResult],
        alpha: float
    ) -> List[RetrievalResult]:
        """Weighted score fusion"""
        # Normalize scores to 0-1
        def normalize(results):
            if not results:
                return {}
            max_s = max(r.score for r in results)
            min_s = min(r.score for r in results)
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
                fused.append(RetrievalResult(
                    id=doc_id,
                    text=orig.text,
                    metadata=orig.metadata,
                    score=fused_score,
                    source="weighted_fusion"
                ))
        
        fused.sort(key=lambda x: x.score, reverse=True)
        return fused
    
    async def embed_query(self, query: str) -> List[float]:
        """Generate query embedding"""
        # Use the embedding service
        from services.documents.embeddings import EmbeddingService
        # ... generate embedding
        pass
```

## Search Request/Response Models

```python
# services/retrieval/schemas.py
@dataclass
class SearchRequest:
    query: str
    top_k: int = 10
    minimum_score: float = 0.3
    filters: dict = None
    search_type: str = "vector"  # vector, hybrid, bm25

@dataclass
class HybridSearchRequest(SearchRequest):
    alpha: float = 0.5
    use_rrf: bool = True
    rrf_k: int = 60

@dataclass
class RetrievalResult:
    id: str
    text: str
    metadata: dict
    score: float
    source: str = "vector"
    vector_rank: int = None
    bm25_rank: int = None
    rerank_score: float = None

@dataclass
class RetrievalResponse:
    results: List[RetrievalResult]
    total_found: int
    search_time_ms: float
```

## API Endpoints

```python
# presentation/api/v1/routes/retrieval.py
@router.post("/search")
async def search(
    request: SearchRequest,
    org_id: str = Depends(get_current_organization_id),
    service: RetrievalService = Depends(get_retrieval_service)
):
    return await service.search(
        query=request.query,
        org_id=org_id,
        kb_ids=request.kb_ids or await get_user_kb_ids(org_id),
        top_k=request.top_k,
        minimum_score=request.minimum_score,
        filters=request.filters
    )

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

@router.post("/rerank")
async def rerank(
    request: RerankRequest,
    org_id: str = Depends(get_current_organization_id),
    service: RetrievalService = Depends(get_retrieval_service)
):
    return await service.rerank(
        query=request.query,
        documents=request.documents,
        top_k=request.top_k
    )
```

## Monitoring

```python
# Metrics
retrieval_search_time = Histogram(
    "retrieval_search_seconds",
    "Retrieval search time",
    ["type"]  # vector, hybrid, bm25
)

retrieval_results_count = Histogram(
    "retrieval_results_count",
    "Number of results returned"
)

retrieval_score_distribution = Histogram(
    "retrieval_score",
    "Result scores",
    ["type"]
)

# In service
async def search(self, ...):
    start = time.perf_counter()
    results = await self._search(...)
    retrieval_search_time.labels(type="vector").observe(time.perf_counter() - start)
    retrieval_results_count.observe(len(results))
    for r in results:
        retrieval_score_distribution.labels(type="vector").observe(r.score)
    return results
```