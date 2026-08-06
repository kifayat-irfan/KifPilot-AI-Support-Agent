# Cross-Encoder Re-ranking

## Overview

Cross-encoder reranking uses a transformer model to score query-document pairs for precise relevance judgment, applied after initial retrieval.

## Why Rerank?

| Stage | Method | Speed | Accuracy |
|-------|--------|-------|----------|
| Initial | Vector/BM25 | Fast | Medium |
| Rerank | Cross-Encoder | Slower | High |

Cross-encoders attend to both query and document simultaneously, capturing fine-grained interactions.

## Model: ms-marco-MiniLM-L-6-v2

```
Architecture: MiniLM (6 layers, 384 hidden)
Training: MS MARCO passage ranking
Input: [CLS] Query [SEP] Document [SEP]
Output: Single relevance score (sigmoid)
Max Length: 512 tokens
Batch Size: 16-32
```

## Reranker Service

```python
# services/reranker/service.py
class RerankerService:
    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        device: str = "cpu",
        max_candidates: int = 20,
        max_results: int = 5,
        batch_size: int = 16,
        timeout: float = 5.0,
        min_score: float = 0.0
    ):
        self.model_name = model_name
        self.device = device
        self.max_candidates = max_candidates
        self.max_results = max_results
        self.batch_size = batch_size
        self.timeout = timeout
        self.min_score = min_score
        
        self._model = None
        self._tokenizer = None
        self._initialized = False
    
    async def initialize(self):
        """Lazy initialization"""
        if self._initialized:
            return
        
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        import torch
        
        self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
        self._model.to(self.device)
        self._model.eval()
        
        self._initialized = True
    
    async def score(self, pairs: List[Tuple[str, str]]) -> List[float]:
        """Score query-document pairs"""
        if not pairs:
            return []
        
        await self.initialize()
        
        # Limit candidates
        pairs = pairs[:self.max_candidates]
        
        scores = []
        for i in range(0, len(pairs), self.batch_size):
            batch = pairs[i:i + self.batch_size]
            batch_scores = await self._score_batch(batch)
            scores.extend(batch_scores)
        
        return scores
    
    async def _score_batch(self, pairs: List[Tuple[str, str]]) -> List[float]:
        import torch
        from transformers import BatchEncoding
        
        # Tokenize
        inputs = self._tokenizer(
            [p[0] for p in pairs],
            [p[1] for p in pairs],
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        ).to(self.device)
        
        # Inference
        with torch.no_grad():
            outputs = self._model(**inputs)
            logits = outputs.logits.squeeze(-1)
            probs = torch.sigmoid(logits)
        
        return probs.cpu().tolist()
    
    async def rerank(
        self,
        query: str,
        documents: List[RetrievalResult],
        top_k: int = None
    ) -> List[RetrievalResult]:
        """Rerank and return top-k"""
        top_k = top_k or self.max_results
        
        if not documents:
            return []
        
        # Limit candidates
        candidates = documents[:self.max_candidates]
        
        # Score pairs
        pairs = [(query, doc.text) for doc in candidates]
        scores = await self.score(pairs)
        
        # Apply scores
        for doc, score in zip(candidates, scores):
            doc.rerank_score = score
            if score < self.min_score:
                doc.score = -1  # Mark for filtering
            else:
                doc.score = score  # Use rerank score as final
        
        # Filter and sort
        filtered = [d for d in candidates if d.score >= self.min_score]
        filtered.sort(key=lambda x: x.rerank_score or 0, reverse=True)
        
        return filtered[:top_k]
```

## ONNX Optimization (Production)

```python
# services/reranker/onnx_service.py
class ONNXRerankerService:
    def __init__(self, model_path: str):
        import onnxruntime as ort
        
        self.session = ort.InferenceSession(
            model_path,
            providers=['CPUExecutionProvider']  # or CUDAExecutionProvider
        )
        self.input_names = [inp.name for inp in self.session.get_inputs()]
        self.output_names = [out.name for out in self.session.get_outputs()]
    
    async def score(self, pairs: List[Tuple[str, str]]) -> List[float]:
        import numpy as np
        
        # Tokenize (using same tokenizer)
        inputs = self.tokenizer(
            [p[0] for p in pairs],
            [p[1] for p in pairs],
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="np"
        )
        
        # Run inference
        ort_inputs = {name: inputs[name] for name in self.input_names}
        outputs = self.session.run(self.output_names, ort_inputs)
        
        # Apply sigmoid
        logits = outputs[0].squeeze(-1)
        probs = 1 / (1 + np.exp(-logits))
        
        return probs.tolist()
```

## Model Export to ONNX

```python
# Export script
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import torch

model_name = "cross-encoder/ms-marco-MiniLM-L-6-v2"
model = AutoModelForSequenceClassification.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# Dummy input
dummy_input = tokenizer(
    ["query"], ["document"],
    padding=True, truncation=True, max_length=512,
    return_tensors="pt"
)

# Export
torch.onnx.export(
    model,
    (dummy_input["input_ids"], dummy_input["attention_mask"]),
    "reranker.onnx",
    input_names=["input_ids", "attention_mask"],
    output_names=["logits"],
    dynamic_axes={
        "input_ids": {0: "batch", 1: "sequence"},
        "attention_mask": {0: "batch", 1: "sequence"},
        "logits": {0: "batch"}
    },
    opset_version=14
)
```

## Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # Reranker
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_MODEL_CACHE_DIR: str = "./models/reranker"
    RERANKER_MAX_CANDIDATES: int = 20
    RERANKER_MAX_RESULTS: int = 5
    RERANKER_BATCH_SIZE: int = 16
    RERANKER_TIMEOUT_SECONDS: float = 5.0
    RERANKER_MIN_RERANK_SCORE: float = 0.0
    
    # ONNX (production)
    RERANKER_USE_ONNX: bool = False
    RERANKER_ONNX_PATH: str = "./models/reranker.onnx"
```

## Reranking in Pipeline

```python
# services/retrieval/service.py
class RetrievalService:
    async def search_with_rerank(self, ...) -> RetrievalResponse:
        # 1. Initial retrieval (vector + BM25)
        results = await self.hybrid_search(query, org_id, kb_ids, top_k=50)
        
        # 2. Rerank top candidates
        if self.settings.RERANKER_ENABLED and results.results:
            results.results = await self.reranker.rerank(
                query=query,
                documents=results.results,
                top_k=top_k
            )
        
        return results
```

## Performance Characteristics

| Metric | Value |
|--------|-------|
| Latency (CPU, batch=16) | ~50-100ms per batch |
| Latency (GPU, batch=16) | ~10-20ms per batch |
| Max candidates | 20 (configurable) |
| Max sequence length | 512 tokens |
| Model size | ~80MB (PyTorch) / ~30MB (ONNX INT8) |

## Monitoring

```python
rerank_time = Histogram("rerank_seconds", "Rerank time")
rerank_candidates = Histogram("rerank_candidates", "Candidates reranked")
rerank_score_distribution = Histogram("rerank_score", "Rerank scores")
rerank_filtered = Counter("rerank_filtered_total", "Results filtered by min_score")
```