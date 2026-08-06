# Developer Guide

This guide covers development setup, architecture, testing, and contribution workflows.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Architecture Overview](#architecture-overview)
4. [Backend Development](#backend-development)
5. [Frontend Development](#frontend-development)
6. [Testing](#testing)
7. [Code Quality](#code-quality)
8. [Debugging](#debugging)
9. [Adding Features](#adding-features)

---

## Development Setup

### Prerequisites

- Python 3.12+
- Node.js 20+
- Ollama (local LLM)
- Git
- Docker (optional)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Initialize database
alembic upgrade head

# Start development server
python -m app.main
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Ollama Setup

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sh

# Pull required models
ollama pull qwen3.5:4b
ollama pull nomic-embed-text

# Verify
ollama list
```

### Docker Development

```bash
# Start all services
docker-compose -f docker-compose.dev.yml up -d

# View logs
docker-compose -f docker-compose.dev.yml logs -f

# Stop
docker-compose -f docker-compose.dev.yml down
```

---

## Project Structure

### Backend (FastAPI)

```
backend/
├── app/
│   ├── api/                 # API routes
│   │   ├── documents.py
│   │   ├── rag.py
│   │   ├── retrieval.py
│   │   ├── streaming.py
│   │   └── ...
│   ├── core/                # Core utilities
│   │   ├── config.py
│   │   ├── security.py
│   │   ├── logging.py
│   │   └── exceptions.py
│   ├── database/            # Database layer
│   │   ├── models.py
│   │   ├── session.py
│   │   └── base.py
│   ├── presentation/        # Presentation layer
│   │   ├── api/v1/          # API v1 routes
│   │   └── middleware/      # Custom middleware
│   ├── security/            # Security modules
│   │   ├── rate_limiter.py
│   │   ├── headers.py
│   │   ├── validation.py
│   │   ├── upload_security.py
│   │   ├── secrets.py
│   │   ├── audit.py
│   │   └── middleware.py
│   ├── services/            # Business logic
│   │   ├── auth/            # Authentication
│   │   ├── documents/       # Document processing
│   │   ├── rag/             # RAG pipeline
│   │   ├── retrieval/       # Search & retrieval
│   │   ├── streaming/       # SSE streaming
│   │   ├── conversation/    # Conversation management
│   │   ├── multitenant/     # Multi-tenant logic
│   │   └── ...
│   ├── evaluation/          # Benchmarking
│   └── monitoring/          # Observability
├── tests/                   # Test suite
│   ├── integration/
│   ├── load/
│   └── regression/
├── migrations/              # Alembic migrations
└── pyproject.toml
```

### Frontend (React + TypeScript + Vite)

```
frontend/
├── src/
│   ├── components/          # Reusable components
│   │   ├── ui/              # Base UI components
│   │   ├── layout/          # Layout components
│   │   ├── auth/            # Auth components
│   │   └── chat/            # Chat components
│   ├── features/            # Feature modules
│   │   ├── admin/
│   │   ├── chat/
│   │   ├── knowledge-base/
│   │   └── documents/
│   ├── pages/               # Page components
│   ├── services/            # API services
│   ├── stores/              # State management (Zustand)
│   ├── types/               # TypeScript types
│   └── utils/               # Utilities
├── tests/
│   ├── e2e/                 # Playwright tests
│   └── integration/
└── package.json
```

---

## Architecture Overview

### Layered Architecture

```
┌─────────────────────────────────────────────────┐
│                  Presentation                   │
│  (API Routes, Middleware, Validation, Auth)    │
├─────────────────────────────────────────────────┤
│                   Services                      │
│  (Auth, Documents, RAG, Retrieval, Streaming)  │
├─────────────────────────────────────────────────┤
│                   Domain                        │
│  (Entities, Repository Interfaces, Use Cases)  │
├─────────────────────────────────────────────────┤
│               Infrastructure                    │
│  (Database, Vector Store, LLM, Cache, Config)  │
└─────────────────────────────────────────────────┘
```

### Key Patterns

- **Dependency Injection**: FastAPI `Depends()` for services
- **Repository Pattern**: Abstract data access
- **Service Layer**: Business logic encapsulation
- **Middleware Stack**: Cross-cutting concerns
- **Event-Driven**: Async processing where appropriate

---

## Backend Development

### Adding a New API Endpoint

1. **Define schema** in `app/presentation/api/v1/schemas/`
2. **Create route** in `app/presentation/api/v1/routes/`
3. **Register route** in `app/presentation/api/v1/routes/__init__.py`
4. **Add service logic** in `app/services/`
5. **Write tests** in `tests/integration/`

### Example: New Endpoint

```python
# app/presentation/api/v1/schemas/my_feature.py
from pydantic import BaseModel, Field

class MyRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    options: dict = Field(default_factory=dict)

class MyResponse(BaseModel):
    result: str
    metadata: dict

# app/presentation/api/v1/routes/my_feature.py
from fastapi import APIRouter, Depends
from app.presentation.api.v1.schemas.my_feature import MyRequest, MyResponse
from app.services.my_feature import MyFeatureService

router = APIRouter(prefix="/my-feature", tags=["My Feature"])

@router.post("/process", response_model=MyResponse)
async def process(
    request: MyRequest,
    service: MyFeatureService = Depends(get_my_feature_service)
):
    return await service.process(request.query, request.options)

# app/presentation/api/v1/routes/__init__.py
from .my_feature import router as my_feature_router
api_router.include_router(my_feature_router)
```

### Database Migrations

```bash
# Create migration
alembic revision --autogenerate -m "Add new table"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Working with Vector Store

```python
from app.services.vectorstore import vector_store_service

# Add documents
await vector_store_service.add_documents(
    collection_name="kb-123",
    documents=[{"id": "1", "text": "content", "metadata": {}}]
)

# Search
results = await vector_store_service.search(
    collection_name="kb-123",
    query_vector=[0.1, 0.2, ...],
    top_k=10
)
```

### Streaming Responses

```python
from fastapi.responses import StreamingResponse

async def stream_generator():
    for token in generate_tokens():
        yield f"data: {json.dumps({'token': token})}\n\n"

return StreamingResponse(
    stream_generator(),
    media_type="text/event-stream"
)
```

---

## Frontend Development

### Component Structure

```tsx
// src/features/chat/components/ChatMessage.tsx
import { ChatMessage as ChatMessageType } from '@/types';

interface ChatMessageProps {
  message: ChatMessageType;
  onRetry?: () => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, onRetry }) => {
  return (
    <div className={`message ${message.role}`}>
      <div className="content">{message.content}</div>
      {message.citations && (
        <CitationPanel citations={message.citations} />
      )}
    </div>
  );
};
```

### State Management (Zustand)

```typescript
// src/stores/chatStore.ts
import { create } from 'zustand';
import { ChatMessage } from '@/types';

interface ChatState {
  messages: ChatMessage[];
  isStreaming: boolean;
  addMessage: (message: ChatMessage) => void;
  setStreaming: (streaming: boolean) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  isStreaming: false,
  addMessage: (message) => set((state) => ({
    messages: [...state.messages, message]
  })),
  setStreaming: (streaming) => set({ isStreaming: streaming })
}));
```

### API Service

```typescript
// src/services/chat.ts
import { api } from './api';

export const chatService = {
  async ask(question: string, options: ChatOptions) {
    const response = await api.post('/chat/ask', { question, ...options });
    return response.data;
  },

  async *stream(question: string, options: ChatOptions) {
    const response = await fetch('/api/v1/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
      body: JSON.stringify({ question, ...options })
    });

    const reader = response.body?.getReader();
    const decoder = new TextDecoder();

    while (true) {
      const { done, value } = await reader!.read();
      if (done) break;
      const chunk = decoder.decode(value);
      for (const line of chunk.split('\n')) {
        if (line.startsWith('data: ')) {
          yield JSON.parse(line.slice(6));
        }
      }
    }
  }
};
```

### Styling (Tailwind CSS)

```tsx
// Use Tailwind utility classes
<button className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors disabled:opacity-50">
  Send
</button>

// Dark mode support
<div className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100">
```

---

## Testing

### Backend Tests

```bash
# Unit tests
pytest tests/ -m "unit" -v

# Integration tests
pytest tests/integration/ -v

# Load tests
pytest tests/load/ -v -m "not stress"

# Regression tests
pytest tests/regression/ -v

# All tests with coverage
pytest tests/ --cov=app --cov-report=html
```

### Writing Integration Tests

```python
# tests/integration/test_my_feature.py
import pytest
from httpx import AsyncClient

class TestMyFeature:
    @pytest.mark.asyncio
    async def test_process_endpoint(self, client: AsyncClient, auth_headers):
        response = await client.post(
            "/api/v1/my-feature/process",
            headers=auth_headers,
            json={"query": "test query"}
        )
        assert response.status_code == 200
        assert "result" in response.json()
```

### Frontend Tests

```bash
# Unit tests
npm test

# E2E tests
npx playwright test

# E2E with UI
npx playwright test --ui
```

### Writing E2E Tests

```python
# frontend/tests/e2e/test_chat.py
import pytest
from playwright.async_api import Page

class TestChat:
    @pytest.mark.asyncio
    async def test_send_message(self, authenticated_page: Page):
        await authenticated_page.fill('textarea[placeholder*="Message"]', "Hello")
        await authenticated_page.click('button:has-text("Send")')
        await authenticated_page.wait_for_selector('[data-role="assistant"]', timeout=30000)
```

---

## Code Quality

### Python (Ruff + MyPy)

```bash
# Format
ruff format .

# Lint
ruff check . --fix

# Type check
mypy app/
```

**Configuration** in `pyproject.toml`:
- Line length: 100
- Target: Python 3.12
- Strict MyPy settings

### TypeScript (ESLint + Prettier)

```bash
# Format
npm run format

# Lint
npm run lint

# Type check
npm run typecheck
```

### Pre-commit Hooks

```bash
# Install
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Debugging

### Backend Debugging

```bash
# VS Code launch.json
{
  "type": "python",
  "request": "launch",
  "name": "Debug FastAPI",
  "module": "app.main",
  "console": "integratedTerminal"
}

# Log levels
LOG_LEVEL=DEBUG python -m app.main

# SQL debugging
# Set in .env: SQL_ECHO=true
```

### Frontend Debugging

```bash
# VS Code launch.json
{
  "type": "chrome",
  "request": "launch",
  "name": "Debug React",
  "url": "http://localhost:5173",
  "webRoot": "${workspaceFolder}/frontend/src"
}

# React DevTools browser extension
# Redux DevTools for Zustand
```

### Common Debug Commands

```bash
# Check API health
curl http://localhost:8000/health

# Test authentication
curl -X POST http://localhost:8000/api/v1/auth/login \
  -d '{"email": "test@test.com", "password": "password"}'

# Inspect database
sqlite3 backend/data/kifpilot.db ".schema"

# Check Ollama
curl http://localhost:11434/api/tags

# Vector store status
curl http://localhost:8000/api/v1/vector/collections
```

---

## Adding Features

### Feature Development Checklist

- [ ] Design API schema (request/response)
- [ ] Implement service layer
- [ ] Add API routes
- [ ] Write unit tests
- [ ] Write integration tests
- [ ] Add frontend components
- [ ] Update TypeScript types
- [ ] Add E2E tests
- [ ] Update documentation
- [ ] Add migration if DB changes
- [ ] Performance test

### Example: Adding Reranker Model

1. **Config**: Add `RERANKER_NEW_MODEL` to `core/config.py`
2. **Service**: Update `services/reranker/model.py`
3. **Schema**: Add model option to `schemas/reranker.py`
4. **Tests**: Add benchmark comparison in `tests/regression/`
5. **Docs**: Update `docs/api/reference.md`

### Database Changes

```bash
# 1. Modify models in app/database/models.py
# 2. Generate migration
alembic revision --autogenerate -m "Add new column"
# 3. Review migration file
# 4. Apply
alembic upgrade head
# 5. Test rollback
alembic downgrade -1
alembic upgrade head
```

---

## Performance Optimization

### Profiling

```python
# Add to endpoint for profiling
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

# ... your code ...

profiler.disable()
stats = pstats.Stats(profiler).sort_stats('cumulative')
stats.print_stats(20)
```

### Caching

```python
from functools import lru_cache
from app.services.cache import cache_service

# Function-level caching
@lru_cache(maxsize=100)
def expensive_computation(key: str) -> Result:
    ...

# Distributed caching
await cache_service.set("key", value, ttl=3600)
value = await cache_service.get("key")
```

### Async Patterns

```python
# Parallel execution
results = await asyncio.gather(
    service.call_a(),
    service.call_b(),
    service.call_c()
)

# Semaphore for rate limiting
semaphore = asyncio.Semaphore(10)

async def limited_call(item):
    async with semaphore:
        return await service.process(item)
```

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Tailwind CSS](https://tailwindcss.com/docs)
- [Zustand](https://github.com/pmndrs/zustand)
- [Playwright](https://playwright.dev/)
- [Pytest](https://docs.pytest.org/)
- [SQLAlchemy](https://docs.sqlalchemy.org/)
- [ChromaDB](https://docs.trychroma.com/)
- [Ollama](https://github.com/ollama/ollama)