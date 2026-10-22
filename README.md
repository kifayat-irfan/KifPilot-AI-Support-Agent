# KifPilot AI Support Agent

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)
![React](https://img.shields.io/badge/React-18+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

A production-ready, multi-tenant AI customer support agent with RAG (Retrieval-Augmented Generation), hybrid search, streaming responses, and enterprise-grade security.

## Features

- **Multi-Tenant Architecture**: Complete organization isolation with role-based access control (RBAC)
- **Document Processing**: PDF, DOCX, TXT, MD support with intelligent chunking and embedding
- **Hybrid Search**: BM25 + Vector similarity with Reciprocal Rank Fusion (RRF)
- **Cross-Encoder Re-ranking**: Precision reranking for improved retrieval accuracy
- **Query Expansion**: Automatic query expansion for better recall
- **Context Compression**: Intelligent context compression to fit token limits
- **Streaming Responses**: Server-Sent Events (SSE) for real-time chat streaming
- **Citation Pipeline**: Automatic source citation with document references
- **Conversation Memory**: Persistent conversation history with context awareness
- **Enterprise Security**: Rate limiting, input validation, audit logging, secure file uploads
- **Observability**: Prometheus metrics, structured logging, distributed tracing, health checks
- **Production Ready**: Docker + Docker Compose deployment, Prometheus/Grafana monitoring stack, CI/CD pipeline

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Ollama (for LLM and embeddings)
- SQLite (development) or PostgreSQL (production)

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env
# Edit .env with your configuration
python -m app.main
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

### Using Docker

```bash
docker-compose up -d
```

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Frontend  │────▶│   Backend   │────▶│   Ollama    │
│  (React)    │     │  (FastAPI)  │     │  (LLM/Emb)  │
└─────────────┘     └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    ▼           ▼
              ┌─────────┐ ┌──────────┐
              │ChromaDB │ │ SQLite/  │
              │(Vector) │ │PostgreSQL│
              └─────────┘ └──────────┘
```

## Documentation

- [API Reference](docs/api/reference.md)
- [User Guide](docs/guides/user-guide.md)
- [Administrator Guide](docs/guides/admin-guide.md)
- [Developer Guide](docs/guides/developer-guide.md)
- [Deployment Guide](docs/guides/deployment-guide.md)
- [Architecture Guide](docs/architecture/overview.md)
- [Troubleshooting](docs/guides/troubleshooting.md)
- [Performance Tuning](docs/guides/performance-tuning.md)
- [Backup & Restore](docs/guides/backup-restore.md)

## Configuration

Key environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Database connection string | `sqlite+aiosqlite:///data/kifpilot.db` |
| `OLLAMA_BASE_URL` | Ollama server URL | `http://localhost:11434` |
| `OLLAMA_CHAT_MODEL` | Chat model name | `qwen3.5:4b` |
| `OLLAMA_EMBED_MODEL` | Embedding model name | `nomic-embed-text` |
| `SECRET_KEY` | JWT secret key | Required in production |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:5173` |

See [.env.example](backend/.env.example) for complete configuration.

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login
- `POST /api/v1/auth/logout` - Logout
- `POST /api/v1/auth/refresh` - Refresh token
- `GET /api/v1/auth/me` - Current user info

### Documents
- `POST /api/v1/documents/upload` - Upload document
- `GET /api/v1/documents` - List documents
- `GET /api/v1/documents/{id}` - Get document
- `PATCH /api/v1/documents/{id}` - Update metadata
- `DELETE /api/v1/documents/{id}` - Delete document
- `POST /api/v1/documents/{id}/restore` - Restore deleted

### Knowledge Bases
- `POST /api/v1/knowledge-bases` - Create KB
- `GET /api/v1/knowledge-bases` - List KBs
- `POST /api/v1/knowledge-bases/{id}/documents` - Add docs to KB

### Chat & RAG
- `POST /api/v1/chat/ask` - Non-streaming chat
- `POST /api/v1/chat/stream` - Streaming chat (SSE)
- `POST /api/v1/rag/query` - RAG query with citations
- `POST /api/v1/rag/stream` - Streaming RAG

### Retrieval
- `POST /api/v1/retrieval/search` - Vector search
- `POST /api/v1/retrieval/hybrid-search` - Hybrid search
- `POST /api/v1/retrieval/rerank` - Cross-encoder rerank
- `POST /api/v1/retrieval/expand-query` - Query expansion
- `POST /api/v1/retrieval/compress-context` - Context compression

### Conversations
- `POST /api/v1/conversations` - Create conversation
- `GET /api/v1/conversations` - List conversations
- `POST /api/v1/conversations/{id}/messages` - Send message
- `GET /api/v1/conversations/{id}/messages` - Get messages

## Testing

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test

# E2E tests
cd frontend
npx playwright test
```

## Deployment

### Production Checklist
- [ ] Set `APP_ENV=production`
- [ ] Configure strong `SECRET_KEY`
- [ ] Use PostgreSQL for database
- [ ] Enable HTTPS/TLS
- [ ] Configure reverse proxy (nginx)
- [ ] Set up monitoring (Prometheus/Grafana)
- [ ] Configure log aggregation
- [ ] Set up backup strategy

See [Deployment Guide](docs/guides/deployment-guide.md) for detailed instructions.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.

## Security

See [SECURITY.md](SECURITY.md) for security policies and vulnerability reporting.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- Documentation: [docs/](docs/)
- Issues: [GitHub Issues](https://github.com/kifpilot/ai-support-agent/issues)
- Discussions: [GitHub Discussions](https://github.com/kifpilot/ai-support-agent/discussions)