# Backend Architecture

## Overview

FastAPI application with clean architecture, dependency injection, and async-first design.

```
app/
├── main.py                 # Application factory, lifespan, middleware stack
├── core/                   # Core infrastructure
│   ├── config.py           # Pydantic Settings (env-based config)
│   ├── security.py         # JWT, password hashing, token verification
│   ├── logging.py          # Structured logging (structlog)
│   ├── exceptions.py       # Custom exception hierarchy
│   └── database.py         # Database engine, session management
├── presentation/           # API layer
│   ├── api/                # Routes v1
│   │   ├── router.py       # Main router aggregation
│   │   ├── health.py       # Health checks
│   │   ├── auth.py         # Authentication endpoints
│   │   ├── documents.py    # Document CRUD + upload
│   │   ├── knowledge_bases.py
│   │   ├── retrieval.py    # Search, hybrid, rerank, expand, compress
│   │   ├── rag.py          # RAG query + streaming
│   │   ├── streaming.py    # Chat streaming (SSE)
│   │   ├── citations.py    # Citation endpoints
│   │   └── ollama.py       # Ollama model management
│   └── middleware/         # Custom middleware
│       ├── logging.py      # Request logging + correlation IDs
│       └── error_handling.py # Global exception handler
├── security/               # Security modules
│   ├── rate_limiter.py     # Tier-based token bucket
│   ├── headers.py          # Security headers middleware
│   ├── validation.py       # Input sanitization (SQLi, XSS, CMDi)
│   ├── upload_security.py  # File validation, MIME, zip bomb
│   ├── secrets.py          # Secrets management, rotation
│   ├── audit.py            # Audit logging
│   └── middleware.py       # Security middleware stack
├── services/               # Business logic layer
│   ├── auth/               # Authentication & authorization
│   │   ├── service.py      # AuthService (login, register, tokens)
│   │   ├── repository.py   # AuthRepository (users, roles, perms)
│   │   ├── dependencies.py # FastAPI deps (get_current_user, require_perm)
│   │   ├── jwt.py          # Token create/verify
│   │   ├── schemas.py      # Auth DTOs
│   │   └── exceptions.py   # Auth errors
│   ├── documents/          # Document processing
│   │   ├── service.py      # DocumentService (upload, process, CRUD)
│   │   ├── processor.py    # Text extraction (PDF, DOCX, TXT)
│   │   ├── chunker.py      # Text chunking (recursive, semantic)
│   │   ├── embeddings.py   # Embedding generation
│   │   ├── schemas.py      # Document DTOs
│   │   └── exceptions.py   # Document errors
│   ├── rag/                # RAG pipeline
│   │   ├── service.py      # RAGService (query, stream)
│   │   ├── answer_generator.py # LLM answer generation
│   │   ├── prompt_builder.py   # Prompt templates
│   │   ├── guardrails.py   # Input/output validation
│   │   ├── schemas.py      # RAG DTOs
│   │   └── exceptions.py   # RAG errors
│   ├── retrieval/          # Search & retrieval
│   │   ├── service.py      # RetrievalService
│   │   ├── search.py       # Vector + BM25 + Hybrid + RRF
│   │   ├── ranking.py      # Cross-encoder reranking
│   │   ├── filters.py      # Metadata filtering
│   │   ├── context_builder.py # Context assembly + compression
│   │   ├── schemas.py      # Retrieval DTOs
│   │   └── exceptions.py   # Retrieval errors
│   ├── streaming/          # SSE streaming
│   │   ├── service.py      # StreamingService
│   │   ├── events.py       # SSE event definitions
│   │   ├── schemas.py      # Stream request/response
│   │   └── exceptions.py   # Streaming errors
│   ├── conversation/       # Conversation management
│   │   ├── service.py      # ConversationService
│   │   ├── session.py      # Session handling
│   │   └── schemas.py      # Conversation DTOs
│   ├── multitenant/        # Multi-tenancy
│   │   ├── service.py      # OrganizationService
│   │   ├── repository.py   # Org/User membership
│   │   ├── schemas.py      # Org DTOs
│   │   ├── dependencies.py # get_current_org_id
│   │   └── exceptions.py   # Multi-tenant errors
│   ├── llm/                # LLM abstraction
│   │   ├── client.py       # OllamaClient
│   │   ├── service.py      # LLMService
│   │   ├── models.py       # Model configs
│   │   └── exceptions.py   # LLM errors
│   ├── vectorstore/        # Vector store abstraction
│   │   ├── client.py       # ChromaClient
│   │   ├── service.py      # VectorStoreService
│   │   ├── collections.py  # Collection management
│   │   ├── embeddings.py   # Embedding handling
│   │   ├── models.py       # Vector DTOs
│   │   └── exceptions.py   # Vector errors
│   ├── evaluation/         # Benchmarking
│   │   ├── runner.py       # EvaluationRunner
│   │   ├── benchmark.py    # BenchmarkSuite
│   │   ├── metrics.py      # Metrics computation
│   │   ├── report.py       # Report generation
│   │   ├── datasets.py     # Dataset loading
│   │   └── schemas.py      # Evaluation DTOs
│   └── monitoring/         # Observability
│       ├── metrics.py      # Prometheus metrics
│       ├── tracing.py      # OpenTelemetry tracing
│       ├── logging.py      # Structured logging
│       ├── health.py       # Health checks
│       ├── exporters.py    # Metrics exporters
│       └── middleware.py   # Monitoring middleware
├── database/               # Database layer
│   ├── models.py           # SQLAlchemy models
│   ├── session.py          # Async session management
│   └── base.py             # Base model, mixins
├── infrastructure/         # External integrations
│   ├── database/           # DB repositories
│   ├── vector_store/       # ChromaDB implementation
│   └── llm/                # Ollama implementation
├── application/            # Use cases (optional)
│   ├── use_cases/
│   ├── interfaces/
│   └── dto/
├── domain/                 # Domain models
│   ├── entities/
│   └── repositories/
└── evaluation/             # Benchmarking package
```

## Key Design Patterns

### Dependency Injection

```python
# FastAPI Depends() for service injection
async def get_document_service(
    db: AsyncSession = Depends(get_db_session),
    vector_store: VectorStoreService = Depends(get_vector_store_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> DocumentService:
    return DocumentService(db, vector_store, embedding_service)

# Usage in routes
@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service)
):
    return await service.upload(file)
```

### Repository Pattern

```python
# Interface
class DocumentRepository(ABC):
    @abstractmethod
    async def create(self, doc: Document) -> Document: ...
    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[Document]: ...
    @abstractmethod
    async def list(self, filters: DocumentFilters) -> List[Document]: ...

# Implementation
class SQLDocumentRepository(DocumentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, doc: Document) -> Document:
        self.session.add(doc)
        await self.session.flush()
        return doc
```

### Service Layer

```python
class DocumentService:
    def __init__(
        self,
        repo: DocumentRepository,
        vector_store: VectorStoreService,
        embedding_service: EmbeddingService,
        chunker: Chunker,
        processor: DocumentProcessor
    ):
        self.repo = repo
        self.vector_store = vector_store
        self.embeddings = embedding_service
        self.chunker = chunker
        self.processor = processor
    
    async def upload(self, file: UploadFile, metadata: DocumentMetadata) -> Document:
        # 1. Validate file
        # 2. Extract text
        # 3. Chunk text
        # 4. Generate embeddings
        # 5. Store vectors
        # 6. Save document metadata
        # 7. Update BM25 index
        return document
```

## Async Architecture

### Async Database

```python
# database/session.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

async_session_maker = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

### Async Services

```python
# All service methods are async
class DocumentService:
    async def upload(self, ...) -> Document:
        text = await self.processor.extract(file)        # Async I/O
        chunks = await self.chunker.chunk(text)          # CPU-bound (thread pool)
        embeddings = await self.embeddings.generate(chunks)  # Async HTTP to Ollama
        await self.vector_store.add(vectors)             # Async DB
        doc = await self.repo.create(doc)                # Async DB
        return doc
```

### Concurrency Control

```python
# Semaphore for external API rate limiting
class OllamaClient:
    def __init__(self):
        self._semaphore = asyncio.Semaphore(4)  # Max 4 concurrent requests
    
    async def generate(self, prompt: str) -> str:
        async with self._semaphore:
            return await self._generate(prompt)

# Task groups for parallel processing
async def process_documents(files: List[UploadFile]) -> List[Document]:
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(service.upload(f)) for f in files]
    return [task.result() for task in tasks]
```

## Document Processing Pipeline

```
Upload Request
      │
      ▼
┌─────────────────┐
│ Security Check  │  ← MIME type, extension, size, executable scan
│ (middleware)    │     Zip bomb detection, secure filename
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Text Extraction │  ← PDF (pymupdf), DOCX (python-docx), TXT/MD (direct)
│ Processor       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Content Hash    │  ← SHA256 for duplicate detection
│ (deduplication) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Chunking        │  ← RecursiveCharacterTextSplitter
│ (1000/200)      │     Configurable size/overlap
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Embedding Gen   │  ← Batch embedding via Ollama
│ (nomic-embed)   │     Async, batched, retry with backoff
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Vector Store    │  ← ChromaDB collection per KB
│ (ChromaDB)      │     Document + chunk vectors + metadata
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ BM25 Index      │  ← In-memory BM25 per KB
│ (update)        │     Persisted to disk
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Persist Doc     │  ← PostgreSQL: document, chunks, metadata
│ Metadata        │
└─────────────────┘
```

## Retrieval Pipeline

```
Query
  │
  ▼
┌─────────────────┐
│ Query Expansion │  ← Rule-based + LLM-based
│ (optional)      │     Cached, max 5 expansions
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Hybrid Search   │
│ ├─ Vector Search│  ← ChromaDB similarity (cosine)
│ │  (embeddings) │     top_k * 2 candidates
│ ├─ BM25 Search  │  ← Lexical search
│ │  (lexical)    │     top_k * 2 candidates
│ └─ RRF Fusion   │  ← Reciprocal Rank Fusion (k=60)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Cross-Encoder   │  ← ms-marco-MiniLM-L-6-v2
│ Re-ranking      │     Batch scoring, top 20 → top 5
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context Builder │
│ ├─ Filter       │  ← Score threshold, metadata filters
│ ├─ Compress     │  ← Token budget (8k), priority-based
│ └─ Assemble     │  ← Ordered by relevance, cited
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Context + Query │  ← Ready for LLM
└─────────────────┘
```

## RAG Pipeline

```
Question + Context
      │
      ▼
┌─────────────────┐
│ Guardrails      │  ← Input validation, PII detection, injection check
│ (input)         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Prompt Builder  │
│ ├─ System Prompt│  ← Role, instructions, constraints
│ ├─ Context      │  ← Retrieved docs with citations
│ ├─ Question     │  ← User question
│ └─ Examples     │  ← Few-shot if configured
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ LLM Generation  │  ← Ollama (qwen3.5:4b)
│ ├─ Streaming    │     Token-by-token via SSE
│ ├─ Temperature  │     0.1 for factual, 0.7 for creative
│ └─ Stop Sequences│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Guardrails      │  ← Output validation, citation verification
│ (output)        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Citation        │  ← Match generated text to source chunks
│ Attribution     │     Semantic similarity matching
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Response        │  ← Answer + citations + confidence + metadata
└─────────────────┘
```

## Streaming Architecture

```
Client                          Server
  │                                │
  ├─ POST /chat/stream ──────────► │
  │                                ├─ Auth, rate limit, validate
  │                                ├─ Create event generator
  │                                │
  │ ◄── 200 OK (text/event-stream)─┤
  │                                │
  ├─ Event: start ◄────────────────┤  { session_id }
  ├─ Event: retrieval ◄────────────┤  { chunks_found, time_ms }
  ├─ Event: token ◄────────────────┤  { text, token_id } (repeated)
  ├─ Event: citations ◄────────────┤  { citations[] }
  ├─ Event: complete ◄─────────────┤  { confidence, sources, time_ms }
  │                                │
  │ (client disconnect)            ├─ Detect disconnect → cancel generation
  │                                │
```

### SSE Implementation

```python
# streaming/events.py
class SSEFormatter:
    @staticmethod
    def format_event(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data)}\n\n"
    
    @staticmethod
    def format_error(message: str, code: str) -> str:
        return SSEFormatter.format_event("error", {"message": message, "code": code})

# streaming/service.py
class StreamingService:
    async def stream_chat(self, request: StreamChatRequest) -> AsyncGenerator[str, None]:
        try:
            # Start event
            yield SSEFormatter.format_event("start", {"session_id": session_id})
            
            # Retrieval
            chunks = await self.retrieval.search(request)
            yield SSEFormatter.format_event("retrieval", {
                "chunks_found": len(chunks),
                "time_ms": retrieval_time
            })
            
            # Token streaming
            async for token in self.llm.stream_generate(prompt):
                if await self._check_disconnected(): break
                yield SSEFormatter.format_event("token", {"text": token})
            
            # Citations
            citations = self._extract_citations(answer, chunks)
            yield SSEFormatter.format_event("citations", {"citations": citations})
            
            # Complete
            yield SSEFormatter.format_event("complete", {
                "confidence": confidence,
                "sources_found": len(chunks),
                "response_time_ms": total_time
            })
        except Exception as e:
            yield SSEFormatter.format_error(str(e), "STREAM_ERROR")
```

## Multi-Tenant Architecture

### Organization Isolation

```python
# All queries auto-filtered by organization
class DocumentService:
    async def list(self, org_id: str, filters: DocumentFilters) -> List[Document]:
        # Org filter automatically applied
        stmt = select(Document).where(Document.organization_id == org_id)
        if filters.category:
            stmt = stmt.where(Document.category == filters.category)
        return await self.repo.list(stmt)

# Vector store: separate collections per KB per org
class VectorStoreService:
    def _get_collection_name(self, kb_id: str, org_id: str) -> str:
        return f"org_{org_id}_kb_{kb_id}"
```

### Quota Enforcement

```python
class MultitenantService:
    async def check_quota(self, org_id: str, resource: str, amount: int = 1) -> bool:
        quotas = {
            "documents": 10000,
            "knowledge_bases": 50,
            "conversations": 1000,
            "daily_queries": 10000,
            "storage_bytes": 10 * 1024 * 1024 * 1024  # 10GB
        }
        current = await self.get_usage(org_id, resource)
        return current + amount <= quotas[resource]
```

## Security Middleware Stack

```python
# main.py - Middleware order (outermost first)
def create_app():
    app = FastAPI(...)
    
    # 1. Security headers (outermost - adds to all responses)
    app = SecurityHeadersMiddleware(app, config)
    
    # 2. Abuse protection (failed login, large payload, streaming limits)
    app = AbuseProtectionMiddleware(app, config)
    app = StreamingAbuseProtectionMiddleware(app, config)
    
    # 3. Main security (rate limit, input validation, audit)
    app = SecurityMiddleware(app, config, audit_logger, input_validator)
    
    # 4. Standard middleware
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(MonitoringMiddleware)
    
    # 5. CORS
    app.add_middleware(CORSMiddleware, ...)
    
    return app
```

## Monitoring Integration

### Metrics Collection

```python
# monitoring/metrics.py
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests",
    ["method", "endpoint", "status"]
)

http_request_duration = Histogram(
    "http_request_duration_seconds", "Request duration",
    ["method", "endpoint"]
)

ai_generation_time = Histogram(
    "ai_generation_time_seconds", "LLM generation time",
    ["model", "streaming"]
)

retrieval_time = Histogram(
    "retrieval_time_seconds", "Retrieval pipeline time",
    ["type"]  # vector, bm25, hybrid, rerank
)
```

### Tracing

```python
# monitoring/tracing.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Usage
@tracer.start_as_current_span("retrieval.hybrid_search")
async def hybrid_search(query: str, top_k: int):
    with tracer.start_as_current_span("retrieval.vector") as span:
        vector_results = await vector_search(query, top_k)
        span.set_attribute("results.count", len(vector_results))
    
    with tracer.start_as_current_span("retrieval.bm25") as span:
        bm25_results = await bm25_search(query, top_k)
    
    with tracer.start_as_current_span("retrieval.rrf") as span:
        return rrf_fusion(vector_results, bm25_results)
```

## Configuration Management

```python
# core/config.py
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    # App
    APP_NAME: str = "KifPilot AI Support Agent"
    APP_ENV: str = "development"
    DEBUG: bool = True
    
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///data/kifpilot.db"
    
    # Vector Store
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    
    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_CHAT_MODEL: str = "qwen3.5:4b"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"
    
    # Security
    SECRET_KEY: str  # Required in production
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    ALGORITHM: str = "HS256"
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173"]
    
    # Document Processing
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: List[str] = [".pdf", ".docx", ".txt", ".md"]
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    
    # Retrieval
    RETRIEVAL_MIN_SCORE: float = 0.3
    RETRIEVAL_MAX_CONTEXT: int = 8000
    HYBRID_RRF_K: int = 60
    
    # Reranker
    RERANKER_ENABLED: bool = True
    RERANKER_MODEL_NAME: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    RERANKER_MAX_CANDIDATES: int = 20
    
    # Query Expansion
    QUERY_EXPANSION_ENABLED: bool = True
    QUERY_EXPANSION_MAX_QUERIES: int = 5
    
    # Context Compression
    CONTEXT_COMPRESSION_ENABLED: bool = True
    CONTEXT_COMPRESSION_MAX_TOKENS: int = 8000
    
    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024
```

## Error Handling

```python
# core/exceptions.py
class KifPilotException(Exception):
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}

class DocumentNotFoundError(KifPilotException):
    def __init__(self, doc_id: str):
        super().__init__("DOCUMENT_NOT_FOUND", f"Document {doc_id} not found", {"doc_id": doc_id})

class FileValidationError(KifPilotException):
    def __init__(self, message: str, details: dict = None):
        super().__init__("FILE_VALIDATION_ERROR", message, details)

# presentation/middleware/error_handling.py
class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            return await call_next(request)
        except KifPilotException as e:
            logger.error("Application error", code=e.code, details=e.details)
            http_exc = http_exception_from_kifpilot(e)
            return JSONResponse(status_code=http_exc.status_code, content=http_exc.detail)
        except Exception as e:
            logger.exception("Unexpected error")
            return JSONResponse(status_code=500, content={"code": "INTERNAL_ERROR", "message": "Internal server error"})
```