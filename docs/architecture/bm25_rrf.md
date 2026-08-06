# BM25 + RRF Deep Dive

## BM25 Scoring Details

### Term Frequency Component
```
TF = f(q,D) * (k1 + 1) / (f(q,D) + k1)
```
- `k1` controls term frequency saturation
- Higher k1 = less saturation = longer docs can score higher
- Default k1=1.5 balances well

### Inverse Document Frequency
```
IDF = ln((N - n + 0.5) / (n + 0.5) + 1)
```
- `N` = total documents
- `n` = documents containing term
- +0.5 smoothing prevents division by zero
- +1 ensures positive scores

### Length Normalization
```
LengthNorm = 1 / (1 - b + b * |D|/avgdl)
```
- `b=0`: no length normalization
- `b=1`: full length normalization
- `b=0.75`: partial normalization (default)

### Complete BM25 Formula
```
Score = Σ IDF(q) * TF * LengthNorm
```

## RRF Mathematical Properties

### Rank-Based Fusion
- Only uses rank positions, not raw scores
- Immune to score calibration differences
- Works when vector scores [0,1] and BM25 scores [0,∞)

### Parameter k
```
RRF = Σ 1/(k + rank_i)
```

| k value | Behavior |
|---------|----------|
| k=1 | Very aggressive, top rank dominates |
| k=10 | Moderate |
| k=60 | Standard (TREC default) |
| k=100 | Conservative, more uniform |

### Theoretical Properties
1. **Monotonic**: Better rank always increases score
2. **Bounded**: Max score = Σ 1/k = m/k (m=number of lists)
3. **Scale-invariant**: Works with any score distribution

## Implementation Optimizations

### Pre-filtering
```python
def search(self, query, top_k):
    # Get more candidates than needed for fusion
    candidates = top_k * self.candidate_multiplier
    vector_results = vector_search(query, candidates)
    bm25_results = bm25_search(query, candidates)
    
    # Fuse
    return rrf_fusion(vector_results, bm25_results, k=self.rrf_k)[:top_k]
```

### Parallel Search
```python
async def hybrid_search(self, query, ...):
    # Run vector and BM25 in parallel
    vector_task = asyncio.create_task(self.vector_search(query, ...))
    bm25_task = asyncio.create_task(self.bm25_search(query, ...))
    
    vector_results, bm25_results = await asyncio.gather(vector_task, bm25_task)
    
    return self._rrf_fusion(vector_results, bm25_results)
```

## Evaluation Metrics

### Recall@k
```python
def recall_at_k(results, relevant_ids, k):
    retrieved = set(r.id for r in results[:k])
    relevant = set(relevant_ids)
    return len(retrieved & relevant) / len(relevant) if relevant else 0
```

### NDCG@k
```python
def ndcg_at_k(results, relevance_scores, k):
    dcg = sum(rel / log2(i+2) for i, rel in enumerate(relevance_scores[:k]))
    ideal = sorted(relevance_scores, reverse=True)
    idcg = sum(rel / log2(i+2) for i, rel in enumerate(ideal[:k]))
    return dcg / idcg if idcg > 0 else 0
```

## Testing Hybrid Quality

```python
class TestHybridSearch:
    @pytest.mark.asyncio
    async def test_hybrid_better_than_individual(self):
        # Hybrid should outperform either alone
        hybrid = await service.hybrid_search(query)
        vector = await service.vector_search(query)
        bm25 = await service.bm25_search(query)
        
        # Evaluate with ground truth
        assert recall(hybrid) >= recall(vector)
        assert recall(hybrid) >= recall(bm25)
    
    @pytest.mark.asyncio
    async def test_rrf_vs_weighted(self):
        # RRF typically more robust
        rrf_results = await service.hybrid_search(query, use_rrf=True)
        weighted = await service.hybrid_search(query, use_rrf=False, alpha=0.5)
        
        assert ndcg(rrf_results) >= ndcg(weighted) - 0.05
```