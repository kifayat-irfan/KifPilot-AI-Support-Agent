# Query Expansion

## Overview

Automatic query expansion generates additional search queries to improve recall by capturing synonyms, related terms, and alternative phrasings.

## Expansion Strategies

### 1. Rule-Based Expansion
- Synonym dictionary lookup
- Domain-specific term expansion
- Abbreviation expansion
- Language-specific rules

### 2. LLM-Based Expansion
- Generate alternative phrasings
- Decompose complex queries
- Add context-aware terms

### 3. Pseudo-Relevance Feedback
- Use top retrieved docs
- Extract key terms
- Reformulate query

## Implementation

```python
# services/retrieval/query_expansion.py
class QueryExpansionService:
    def __init__(
        self,
        llm_client: OllamaClient,
        max_expansions: int = 5,
        timeout: float = 3.0,
        use_llm: bool = False,
        cache_ttl: int = 3600
    ):
        self.llm = llm_client
        self.max_expansions = max_expansions
        self.timeout = timeout
        self.use_llm = use_llm
        self._cache: Dict[str, Tuple[List[str], float]] = {}  # query -> (expansions, timestamp)
        self.cache_ttl = cache_ttl
        
        # Rule-based synonyms
        self.synonym_map = {
            "ai": ["artificial intelligence", "machine learning", "ml"],
            "ml": ["machine learning", "artificial intelligence", "deep learning"],
            "api": ["application programming interface", "rest api", "endpoint"],
            "ui": ["user interface", "frontend", "gui"],
            "db": ["database", "data store", "sql"],
            "auth": ["authentication", "authorization", "login", "oauth"],
            "k8s": ["kubernetes", "container orchestration"],
            "ci/cd": ["continuous integration", "continuous deployment", "pipeline"],
        }
    
    async def expand(self, query: str) -> List[str]:
        """Generate expanded queries"""
        # Check cache
        cached = self._get_cached(query)
        if cached:
            return cached
        
        expansions = set([query])  # Always include original
        
        # 1. Rule-based expansion
        rule_expansions = self._rule_based_expand(query)
        expansions.update(rule_expansions)
        
        # 2. LLM-based expansion (if enabled)
        if self.use_llm and len(expansions) < self.max_expansions:
            llm_expansions = await self._llm_expand(query)
            expansions.update(llm_expansions)
        
        # Limit and cache
        result = list(expansions)[:self.max_expansions]
        self._cache_result(query, result)
        
        return result
    
    def _rule_based_expand(self, query: str) -> List[str]:
        """Expand using synonym dictionary"""
        words = query.lower().split()
        expanded = []
        
        for word in words:
            # Direct synonym match
            if word in self.synonym_map:
                expanded.extend(self.synonym_map[word])
            
            # Partial matches
            for key, syns in self.synonym_map.items():
                if key in word or word in key:
                    expanded.extend(syns)
        
        # Generate query variants
        variants = []
        for term in expanded:
            # Replace in query
            for original in words:
                if original in query.lower():
                    variant = query.lower().replace(original, term)
                    if variant != query.lower():
                        variants.append(variant)
        
        return variants
    
    async def _llm_expand(self, query: str) -> List[str]:
        """Generate expansions using LLM"""
        prompt = f"""Generate {self.max_expansions} alternative search queries for: "{query}"

Return only the queries, one per line, no explanations.
Focus on synonyms, related terms, and alternative phrasings."""
        
        try:
            response = await asyncio.wait_for(
                self.llm.generate(
                    model="qwen3.5:4b",
                    prompt=prompt,
                    options={"temperature": 0.7, "top_p": 0.9}
                ),
                timeout=self.timeout
            )
            
            expansions = [
                line.strip() 
                for line in response.response.split('\n') 
                if line.strip() and not line.startswith('#')
            ]
            return expansions[:self.max_expansions]
        except Exception as e:
            logger.warning(f"LLM expansion failed: {e}")
            return []
    
    def _get_cached(self, query: str) -> Optional[List[str]]:
        if query in self._cache:
            result, timestamp = self._cache[query]
            if time.time() - timestamp < self.cache_ttl:
                return result
            else:
                del self._cache[query]
        return None
    
    def _cache_result(self, query: str, result: List[str]):
        self._cache[query] = (result, time.time())
        
        # Simple cache eviction
        if len(self._cache) > 1000:
            # Remove oldest 20%
            sorted_items = sorted(self._cache.items(), key=lambda x: x[1][1])
            for key, _ in sorted_items[:200]:
                del self._cache[key]
```

## Multi-Query Retrieval

```python
# services/retrieval/service.py
class RetrievalService:
    async def search_with_expansion(
        self,
        query: str,
        org_id: str,
        kb_ids: List[str],
        top_k: int = 10,
        expansion_enabled: bool = True
    ) -> RetrievalResponse:
        if not expansion_enabled:
            return await self.search(query, org_id, kb_ids, top_k)
        
        # 1. Generate expanded queries
        expanded = await self.expander.expand(query)
        
        # 2. Search for each expansion
        all_results = []
        for exp_query in expanded:
            results = await self.hybrid_search(exp_query, org_id, kb_ids, top_k)
            for r in results:
                r.metadata["source_query"] = exp_query
            all_results.extend(results)
        
        # 3. Fuse results (RRF across expansions)
        fused = self._fuse_expansions(all_results)
        
        # 4. Return top-k
        fused.sort(key=lambda x: x.score, reverse=True)
        return RetrievalResponse(
            results=fused[:top_k],
            total_found=len(fused),
            search_time_ms=sum(r.search_time_ms for r in all_results)
        )
    
    def _fuse_expansions(self, results: List[RetrievalResult]) -> List[RetrievalResult]:
        """RRF across expansion queries"""
        query_groups = {}
        for r in results:
            q = r.metadata.get("source_query", "original")
            if q not in query_groups:
                query_groups[q] = []
            query_groups[q].append(r)
        
        # Apply RRF across query groups
        k = 60
        all_ids = set()
        ranks = {}
        
        for query, docs in query_groups.items():
            for i, doc in enumerate(docs):
                if doc.id not in ranks:
                    ranks[doc.id] = []
                ranks[doc.id].append(i + 1)
                all_ids.add(doc.id)
        
        fused = []
        for doc_id in all_ids:
            rrf_score = sum(1.0 / (60 + r) for r in ranks[doc_id])
            orig = next(r for r in results if r.id == doc_id)
            fused.append(RetrievalResult(
                id=doc_id,
                text=orig.text,
                metadata=orig.metadata,
                score=rrf_score,
                source="expansion_rrf"
            ))
        
        fused.sort(key=lambda x: x.score, reverse=True)
        return fused
```

## Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # Query Expansion
    QUERY_EXPANSION_ENABLED: bool = True
    QUERY_EXPANSION_MAX_QUERIES: int = 5
    QUERY_EXPANSION_TIMEOUT_SECONDS: float = 2.0
    QUERY_EXPANSION_USE_LLM: bool = False
    QUERY_EXPANSION_LLM_MAX_EXPANSIONS: int = 3
    QUERY_EXPANSION_LLM_TIMEOUT_SECONDS: float = 3.0
    QUERY_EXPANSION_CACHE_ENABLED: bool = True
    QUERY_EXPANSION_CACHE_TTL_SECONDS: int = 3600
```

## API Endpoint

```python
# presentation/api/v1/routes/retrieval.py
@router.post("/expand-query")
async def expand_query(
    request: ExpandQueryRequest,
    org_id: str = Depends(get_current_organization_id),
    expander: QueryExpansionService = Depends(get_query_expander)
):
    expansions = await expander.expand(request.query)
    return ExpandQueryResponse(
        original_query=request.query,
        expanded_queries=expansions
    )

class ExpandQueryRequest(BaseModel):
    query: str
    max_expansions: int = 5

class ExpandQueryResponse(BaseModel):
    original_query: str
    expanded_queries: List[str]
```

## Evaluation

```python
class TestQueryExpansion:
    @pytest.mark.asyncio
    async def test_expansion_improves_recall(self):
        # With expansion, should find more relevant docs
        base_results = await service.search("AI")
        expanded_results = await service.search_with_expansion("AI")
        
        assert len(expanded_results.results) >= len(base_results.results)
    
    @pytest.mark.asyncio
    async def test_synonym_expansion(self):
        expansions = await expander.expand("ML model training")
        assert "machine learning model training" in expansions
        assert "deep learning training" in expansions
    
    @pytest.mark.asyncio
    async def test_caching(self):
        # Second call should be faster (cached)
        await expander.expand("test query")
        start = time.perf_counter()
        await expander.expand("test query")
        assert time.perf_counter() - start < 0.01  # <10ms cached
```