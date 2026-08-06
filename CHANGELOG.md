# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-08-05

### Added
- **Multi-Tenant Architecture**: Complete organization isolation with RBAC
  - Organizations, users, roles (Admin, Manager, Editor, Viewer)
  - Permission-based access control (UPLOAD_DOCUMENTS, DELETE_DOCUMENTS, CHAT, VIEW_SESSIONS, MANAGE_USERS, MANAGE_SETTINGS)
  - Organization member management with role assignment
- **Document Processing Pipeline**
  - Support for PDF, DOCX, TXT, MD, CSV, JSON, XML, HTML
  - Intelligent chunking with configurable size/overlap
  - Content hash-based duplicate detection
  - Metadata extraction (title, category, tags, language)
  - Soft delete with restore capability
- **Vector Storage & Embeddings**
  - ChromaDB integration with persistent collections
  - Multiple embedding models via Ollama (nomic-embed-text)
  - Collection management per knowledge base
- **Hybrid Search (BM25 + Vector)**
  - BM25 lexical search with configurable parameters
  - Vector similarity search with cosine distance
  - Reciprocal Rank Fusion (RRF) with configurable k parameter
  - Configurable score thresholds and result limits
- **Cross-Encoder Re-ranking**
  - ms-marco-MiniLM-L-6-v2 cross-encoder model
  - Batch processing for efficiency
  - Configurable candidate/result limits
  - Minimum rerank score threshold
- **Query Expansion**
  - Rule-based and LLM-based expansion
  - Configurable max expansions
  - Caching with TTL for performance
- **Context Compression**
  - Token-aware context assembly
  - Priority-based document selection
  - Configurable token limits
- **RAG Answer Generation**
  - Structured prompt templates with guardrails
  - Confidence scoring
  - Automatic citation generation with document references
  - Streaming and non-streaming modes
- **Streaming Chat (SSE)**
  - Server-Sent Events for real-time responses
  - Token-by-token streaming with cancellation support
  - Client disconnect detection and cleanup
  - Health check endpoint for streaming service
- **Conversation Memory**
  - Persistent conversation sessions
  - Message history with roles (user/assistant)
  - Context injection for follow-up questions
  - Conversation CRUD operations
- **Citation Pipeline**
  - Inline citations with document/chunk references
  - Citation precision/recall tracking
  - Source text snippets in citations
- **Enterprise Security**
  - **Rate Limiting**: Tier-based (Anonymous: 10/min, Authenticated: 60/min, Admin: 200/min) with special endpoint limits
  - **Security Headers**: CSP, HSTS, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy
  - **Input Validation**: SQL injection, XSS, command injection, path traversal detection
  - **File Upload Security**: MIME type validation, extension filtering, executable detection, zip bomb protection, secure filename generation
  - **Secrets Management**: Environment-based loading, encryption at rest, rotation support, no-secrets logging
  - **Audit Logging**: Login, logout, permission denied, document upload/delete, role changes, org changes, admin actions, suspicious activity
  - **Abuse Protection**: Failed login blocking (5/15min), large payload rejection (10MB), streaming session limits
- **Observability Stack**
  - Prometheus metrics (HTTP, AI, infrastructure, business)
  - Structured JSON logging with correlation IDs
  - OpenTelemetry distributed tracing (Jaeger/OTLP)
  - Health checks (database, vector store, Ollama, disk, memory, CPU)
  - Multi-exporter support (Prometheus, OTLP, Jaeger)
- **Frontend (React 18 + TypeScript + Vite)**
  - Dashboard with statistics and quick actions
  - Document management (upload, list, filter, delete, restore)
  - Knowledge base management
  - Chat interface with streaming support
  - Citation panel with source documents
  - Conversation sidebar with history
  - Organization/user management (admin)
  - Settings and profile management
  - Responsive design with Tailwind CSS
- **Development Tooling**
  - Comprehensive test suite (unit, integration, load, regression)
  - Playwright E2E tests
  - CI/CD pipeline (GitHub Actions)
  - Coverage reporting (HTML, XML, JSON)
  - Benchmark regression detection
  - Automated report generation

### Changed
- N/A (initial release)

### Deprecated
- N/A (initial release)

### Removed
- N/A (initial release)

### Fixed
- N/A (initial release)

### Security
- All security features implemented from ground up
- No known vulnerabilities in initial release

---

## Version History

| Version | Date | Description |
|---------|------|-------------|
| 1.0.0 | 2026-08-05 | Initial production release |