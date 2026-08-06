# Embedding Pipeline

## Overview

Vector embedding generation, storage, and management pipeline using Ollama and ChromaDB.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EMBEDDING PIPELINE                                  │
│                                                                             │
│  Input Text ──▶ Preprocessing ──▶ Batching ──▶ Ollama Embed ──▶ Validation │
│       │              │              │            │              │           │
│       ▼              ▼              ▼            ▼              ▼           │
│  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐     │
│  │ Clean & │   │ Dynamic │   │  Batch  │   │  Model: │   │  Check  │     │
│  │ Normalize│  │ Batching│   │  Size:  │   │ nomic-  │   │  dims   │     │
│  │  Text    │   │  32     │   │         │   │ embed-  │   │  normalize│    │
│  └─────────┘   └─────────┘   └─────────┘   │   text   │   └─────────┘     │
│                                             └─────────┘                    │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │   ChromaDB Store    │
                         │  Collection per KB  │
                         │  Vector + Metadata  │
                         └─────────────────────┘
```

## Embedding Service

```python
# services/documents/embeddings.py
class EmbeddingService:
    def __init__(
        self,
        ollama_client: OllamaClient,
        model: str = "nomic-embed-text",
        batch_size: int = 32,
        max_retries: int = 3
    ):
        self.client = ollama_client
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self._dimension_cache: Optional[int] = None
    
    @property
    def dimension(self) -> int:
        if self._dimension_cache is None:
            # Get dimension from test embedding
            test_emb = asyncio.run(self.generate_single("test"))
            self._dimension_cache = len(test_emb)
        return self._dimension_cache
    
    async def generate(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts with batching and retry"""
        if not texts:
            return []
        
        all_embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            embeddings = await self._generate_batch_with_retry(batch)
            all_embeddings.extend(embeddings)
        
        return all_embeddings
    
    async def _generate_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = await self.client.embed(
                    model=self.model,
                    input=texts
                )
                
                # Validate response
                embeddings = response.embeddings
                if len(embeddings) != len(texts):
                    raise ValueError(f"Embedding count mismatch: {len(embeddings)} vs {len(texts)}")
                
                # Check dimensions
                expected_dim = self.dimension
                for j, emb in enumerate(embeddings):
                    if len(emb) != expected_dim:
                        raise ValueError(f"Embedding {j} has wrong dimension: {len(emb)} vs {expected_dim}")
                
                return embeddings
                
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(f"Embedding batch failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Embedding batch failed after {self.max_retries} attempts: {e}")
        
        raise EmbeddingGenerationError(f"Failed after {self.max_retries} attempts: {last_error}")
    
    async def generate_single(self, text: str) -> List[float]:
        return (await self.generate([text]))[0]
```

## Ollama Client

```python
# services/llm/client.py
class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 120.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session: Optional[aiohttp.ClientSession] = None
        self._semaphore = asyncio.Semaphore(4)  # Limit concurrent requests
    
    async def __aenter__(self):
        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout)
        )
        return self
    
    async def __aexit__(self, *args):
        if self._session:
            await self._session.close()
    
    async def embed(self, model: str, input: List[str]) -> EmbedResponse:
        """Generate embeddings via Ollama /api/embed"""
        async with self._semaphore:
            payload = {"model": model, "input": input}
            
            async with self._session.post(
                f"{self.base_url}/api/embed",
                json=payload
            ) as response:
                if response.status != 200:
                    error = await response.text()
                    raise OllamaError(f"Embedding failed: {error}")
                
                data = await response.json()
                return EmbedResponse(embeddings=data.get("embeddings", []))
    
    async def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        options: dict = None
    ) -> Union[GenerateResponse, AsyncGenerator[str, None]]:
        """Generate text via Ollama /api/generate"""
        async with self._semaphore:
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
                "options": options or {}
            }
            
            if stream:
                return self._stream_generate(payload)
            else:
                async with self._session.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        raise OllamaError(f"Generation failed: {error}")
                    return GenerateResponse(**(await response.json()))
    
    async def _stream_generate(self, payload: dict) -> AsyncGenerator[str, None]:
        async with self._session.post(
            f"{self.base_url}/api/generate",
            json=payload
        ) as response:
            if response.status != 200:
                error = await response.text()
                raise OllamaError(f"Stream generation failed: {error}")
            
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line)
                        if "response" in data:
                            yield data["response"]
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
    
    async def list_models(self) -> List[ModelInfo]:
        async with self._session.get(f"{self.base_url}/api/tags") as response:
            if response.status != 200:
                raise OllamaError("Failed to list models")
            data = await response.json()
            return [ModelInfo(**m) for m in data.get("models", [])]
    
    async def pull_model(self, model: str) -> AsyncGenerator[PullProgress, None]:
        async with self._session.post(
            f"{self.base_url}/api/pull",
            json={"name": model, "stream": True}
        ) as response:
            async for line in response.content:
                if line:
                    try:
                        yield PullProgress(**json.loads(line))
                    except json.JSONDecodeError:
                        continue
    
    async def verify_model(self, model: str) -> bool:
        models = await self.list_models()
        return any(m.name.startswith(model.split(":")[0]) for m in models)
    
    async def health_check(self) -> HealthStatus:
        try:
            async with self._session.get(f"{self.base_url}/api/tags", timeout=5) as resp:
                return HealthStatus(
                    healthy=resp.status == 200,
                    models=await self.list_models() if resp.status == 200 else []
                )
        except Exception:
            return HealthStatus(healthy=False, models=[])
```

## Embedding Models

### Model Configuration

```python
# core/config.py
class Settings(BaseSettings):
    # Embedding models
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    OLLAMA_EMBED_DIMENSION: int = 768  # nomic-embed-text dimension
    
    # Alternative models (for future use)
    EMBEDDING_MODELS: Dict[str, EmbeddingModelConfig] = {
        "nomic-embed-text": EmbeddingModelConfig(
            name="nomic-embed-text",
            dimension=768,
            max_tokens=8192,
            description="General purpose, good quality/speed balance"
        ),
        "mxbai-embed-large": EmbeddingModelConfig(
            name="mxbai-embed-large",
            dimension=1024,
            max_tokens=512,
            description="High quality, larger model"
        ),
        "all-minilm": EmbeddingModelConfig(
            name="all-minilm",
            dimension=384,
            max_tokens=256,
            description="Fast, smaller model"
        ),
    }

@dataclass
class EmbeddingModelConfig:
    name: str
    dimension: int
    max_tokens: int
    description: str
```

### Model Selection

```python
# services/documents/embeddings.py
class EmbeddingService:
    def __init__(self, ollama_client: OllamaClient, settings: Settings):
        self.client = ollama_client
        self.settings = settings
        self.model = settings.OLLAMA_EMBED_MODEL
        self.batch_size = 32
        self._dimension = settings.OLLAMA_EMBED_DIMENSION
    
    async def verify_model_available(self) -> bool:
        """Check if configured embedding model is available in Ollama"""
        models = await self.client.list_models()
        model_names = [m.name for m in models]
        
        # Check exact match or prefix match (e.g., "nomic-embed-text:latest")
        for name in model_names:
            if name.startswith(self.model.split(":")[0]):
                return True
        
        return False
    
    async def get_model_info(self) -> dict:
        """Get info about current embedding model"""
        if self.model in self.settings.EMBEDDING_MODELS:
            config = self.settings.EMBEDDING_MODELS[self.model]
            return {
                "name": config.name,
                "dimension": config.dimension,
                "max_tokens": config.max_tokens,
                "description": config.description
            }
        return {"name": self.model, "dimension": self._dimension}
```

## Vector Normalization

```python
# services/documents/embeddings.py
import numpy as np

class EmbeddingService:
    def _normalize_embedding(self, embedding: List[float]) -> List[float]:
        """L2 normalize embedding for cosine similarity"""
        arr = np.array(embedding, dtype=np.float32)
        norm = np.linalg.norm(arr)
        if norm > 0:
            return (arr / norm).tolist()
        return embedding
    
    async def _generate_batch_with_retry(self, texts: List[str]) -> List[List[float]]:
        # ... existing code ...
        
        # Normalize all embeddings
        normalized = [self._normalize_embedding(emb) for emb in embeddings]
        return normalized
```

## Batch Processing for Large Documents

```python
# services/documents/service.py
class DocumentService:
    async def _generate_embeddings_for_chunks(self, chunks: List[Chunk]) -> List[Chunk]:
        """Generate embeddings for all chunks in a document"""
        texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings
        embeddings = await self.embedding_service.generate(texts)
        
        # Attach to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        return chunks
    
    async def _process_large_document(self, chunks: List[Chunk]) -> List[Chunk]:
        """Process embeddings in smaller batches for very large documents"""
        # For documents with many chunks, process in sub-batches
        # to avoid memory issues and provide progress tracking
        batch_size = 50  # Sub-batch for embedding
        all_chunks = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            processed = await self._generate_embeddings_for_chunks(batch)
            all_chunks.extend(processed)
            
            # Log progress
            logger.info(f"Embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")
        
        return all_chunks
```

## Caching

```python
# services/documents/embeddings.py
class EmbeddingService:
    def __init__(self, ollama_client: OllamaClient, model: str = "nomic-embed-text"):
        self.client = ollama_client
        self.model = model
        self._cache: Dict[str, List[float]] = {}  # Simple in-memory cache
        self._cache_max_size = 10000
    
    def _get_cache_key(self, text: str) -> str:
        return hashlib.sha256(f"{self.model}:{text}".encode()).hexdigest()[:32]
    
    async def generate(self, texts: List[str]) -> List[List[float]]:
        # Check cache
        results = [None] * len(texts)
        uncached_indices = []
        uncached_texts = []
        
        for i, text in enumerate(texts):
            key = self._get_cache_key(text)
            if key in self._cache:
                results[i] = self._cache[key]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)
        
        # Generate for uncached
        if uncached_texts:
            new_embeddings = await self._generate_batch_with_retry(uncached_texts)
            
            # Update cache and results
            for idx, embedding in zip(uncached_indices, new_embeddings):
                results[idx] = embedding
                # Add to cache
                key = self._get_cache_key(texts[idx])
                if len(self._cache) < self._cache_max_size:
                    self._cache[key] = embedding
        
        return results
```

## Monitoring

```python
# Metrics
embedding_generation_time = Histogram(
    "embedding_generation_seconds",
    "Time to generate embeddings",
    ["model", "batch_size"]
)

embedding_batch_size = Histogram(
    "embedding_batch_size",
    "Batch sizes for embedding generation"
)

embedding_cache_hits = Counter(
    "embedding_cache_hits_total",
    "Cache hits for embeddings",
    ["model"]
)

embedding_errors = Counter(
    "embedding_errors_total",
    "Embedding generation errors",
    ["model", "error_type"]
)

# In service
async def generate(self, texts: List[str]) -> List[List[float]]:
    start = time.perf_counter()
    batch_size = len(texts)
    
    try:
        embeddings = await self._generate_batch_with_retry(texts)
        embedding_generation_time.labels(model=self.model, batch_size=str(batch_size)).observe(
            time.perf_counter() - start
        )
        embedding_batch_size.observe(batch_size)
        return embeddings
    except Exception as e:
        embedding_errors.labels(model=self.model, error_type=type(e).__name__).inc()
        raise
```

## Testing

```python
# tests/integration/test_embeddings.py
class TestEmbeddings:
    @pytest.mark.asyncio
    async def test_generate_single(self, embedding_service):
        emb = await embedding_service.generate_single("Test text")
        assert len(emb) == 768
        assert all(isinstance(x, float) for x in emb)
    
    @pytest.mark.asyncio
    async def test_generate_batch(self, embedding_service):
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = await embedding_service.generate(texts)
        assert len(embeddings) == 3
        assert all(len(e) == 768 for e in embeddings)
    
    @pytest.mark.asyncio
    async def test_normalization(self, embedding_service):
        emb = await embedding_service.generate_single("Test")
        norm = sum(x*x for x in emb) ** 0.5
        assert abs(norm - 1.0) < 1e-5  # L2 normalized
    
    @pytest.mark.asyncio
    async def test_caching(self, embedding_service):
        # First call
        emb1 = await embedding_service.generate_single("Cache test")
        # Second call should hit cache
        emb2 = await embedding_service.generate_single("Cache test")
        assert emb1 == emb2
    
    @pytest.mark.asyncio
    async def test_large_batch(self, embedding_service):
        texts = [f"Text {i}" for i in range(100)]
        embeddings = await embedding_service.generate(texts)
        assert len(embeddings) == 100
```