# System Architecture

## Overview

KifPilot AI Support Agent follows a layered, microservices-ready architecture designed for scalability, security, and maintainability.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        EXTERNAL CLIENTS                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │   Web App   │  │  Mobile App │  │   API Client│  │  Webhooks │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────┬─────┘ │
└─────────┼────────────────┼────────────────┼───────────────┼───────┘
          │                │                │               │
          ▼                ▼                ▼               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY / LOAD BALANCER                    │
│                    (nginx / Traefik / Cloud LB)                     │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        FASTAPI APPLICATION                          │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    MIDDLEWARE STACK                           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────────┐  │   │
│  │  │ Security │ │  Rate    │ │  Input   │ │   Monitoring   │  │   │
│  │  │ Headers  │ │ Limiting │ │Validation│ │  (Metrics/Log) │  │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                  │                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                      API ROUTES                               │   │
│  │  /auth  /documents  /kb  /retrieval  /rag  /chat  /convs    │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                  │                                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    SERVICE LAYER                              │   │
│  │ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐  │   │
│  │ │ Auth   │ │ Docs   │ │ RAG    │ │Retrieval│ │ Streaming  │  │   │
│  │ └────────┘ └────────┘ └────────┘ └────────┘ └────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────┬───────────────────────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │    ChromaDB     │    │     Ollama      │
│   (Primary DB)  │    │  (Vector Store) │    │  (LLM/Embed)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  ▼
                    ┌───────────────────────┐
                    │   MONITORING STACK    │
                    │  Prometheus/Grafana   │
                    │  OpenTelemetry/Jaeger │
                    │  Structured Logging   │
                    └───────────────────────┘
```

## Core Components

### 1. API Layer (`app/presentation/api/`)
- **Routes**: RESTful endpoints organized by resource
- **Schemas**: Pydantic models for request/response validation
- **Dependencies**: FastAPI `Depends()` for auth, DB, services
- **Middleware**: Security, logging, monitoring, error handling

### 2. Service Layer (`app/services/`)
- **Auth Service**: JWT tokens, user management, RBAC
- **Document Service**: Upload, processing, chunking, embeddings
- **RAG Service**: Query processing, answer generation, citations
- **Retrieval Service**: Hybrid search, reranking, expansion
- **Streaming Service**: SSE implementation, token streaming
- **Conversation Service**: Session management, message history
- **Multi-tenant Service**: Organization isolation, quotas

### 3. Domain Layer (`app/domain/`)
- **Entities**: Core business objects (User, Document, KB, Conversation)
- **Repository Interfaces**: Abstract data access contracts
- **Use Cases**: Application business rules

### 4. Infrastructure Layer (`app/infrastructure/`)
- **Database**: SQLAlchemy + asyncpg/aiosqlite
- **Vector Store**: ChromaDB client with collection management
- **LLM Client**: Ollama integration with model management
- **Configuration**: Pydantic Settings with env support

## Data Flow

### Document Ingestion Pipeline

```
Upload → Validate → Extract Text → Chunk → Embed → Store Vectors → Update BM25 → Index Complete
  │         │           │          │       │           │              │
  ▼         ▼           ▼          ▼       ▼           ▼              ▼
Security  MIME/Ext   Parser    Chunker  Embedding  ChromaDB      BM25 Index
Headers   Check      (pdf/    (1000/   (nomic-    Collection    Update
         Size Limit  docx/    200)     embed-    + Metadata
                  txt)                  text)
```

### RAG Query Pipeline

```
User Query → Expand → Hybrid Search → Rerank → Compress → Generate → Stream
    │         │         │            │         │          │        │
    ▼         ▼         ▼            ▼         ▼          ▼        ▼
  Guardrails  Rules   BM25 +      Cross-    Token-    Prompt    SSE
  /Validate   /LLM    Vector +    Encoder   Budget    Template  Events
              Expand   RRF                         (8k max)
```

### Streaming Flow

```
Client → POST /chat/stream → Event Generator → SSE Stream → Client
                │                  │                │
                ▼                  ▼                ▼
          Auth/Rate          Async Token      Connection:
          Limit/Validate     Generation       Keep-Alive,
                                                No Buffering,
                                                Auto-Reconnect
```

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| API Framework | FastAPI | 0.109+ |
| Database | SQLAlchemy + PostgreSQL/SQLite | 2.0+ |
| Vector Store | ChromaDB | 0.4+ |
| LLM/Embeddings | Ollama | 0.2+ |
| Auth | python-jose + passlib | 3.3+ / 1.7+ |
| Monitoring | Prometheus + OpenTelemetry | Latest |
| Frontend | React + TypeScript + Vite | 18+ / 5+ / 5+ |
| Styling | Tailwind CSS | 3+ |
| State | Zustand | 4+ |
| Testing | pytest + Playwright | 7+ / 1.4+ |

## Security Architecture

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────┐
│                    NETWORK PERIMETER                        │
│  WAF / DDoS Protection / TLS Termination                    │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    API GATEWAY                              │
│  Rate Limiting / IP Filtering / Request Validation          │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                  APPLICATION SECURITY                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ Security│ │  Input  │ │  File   │ │   Audit &       │   │
│  │ Headers │ │Validation│ │ Upload  │ │  Monitoring     │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    DATA SECURITY                            │
│  Encryption at Rest / Field-level Encryption / Key Rotation │
└─────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
Login Request → Validate Credentials → Generate JWT Pair → Return Tokens
     │                   │                    │               │
     ▼                   ▼                    ▼               ▼
  Rate Limit        bcrypt Verify        Access Token    HttpOnly Cookie
  (5/min)           (12 rounds)          (30 min)        (Optional)
                                                   
Subsequent Requests → Extract Bearer → Verify Signature → Check Expiry → Authorize
       │                    │               │              │           │
       ▼                    ▼               ▼              ▼           ▼
   Middleware           HS256/RS256     Exp/iat claims  Permissions  Service
```

## Deployment Architecture

### Production (Kubernetes)

```
┌─────────────────────────────────────────────────────────────┐
│                      INGRESS (nginx)                        │
│  TLS / Rate Limit / Path Routing / Health Checks            │
└─────────────────────────────────────────────────────────────┘
                              │
         ┌────────────────────┼────────────────────┐
         ▼                    ▼                    ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Frontend Pods  │  Backend Pods     │  Worker Pods     │
│  (Static/SSR)   │  (FastAPI)        │  (Async Jobs)    │
│  HPA: 3-20      │  HPA: 3-50        │  HPA: 1-10       │
└─────────────────┘ └─────────────────┘ └─────────────────┘
         │                    │                    │
         └────────────────────┼────────────────────┘
                              ▼
         ┌─────────────────────────────────────────────┐
         │              SHARED SERVICES                │
         │  PostgreSQL (Primary/Replica)              │
         │  ChromaDB (Cluster)                        │
         │  Ollama (GPU Nodes)                        │
         │  Redis (Cache/Queue)                       │
         │  Prometheus + Grafana + Jaeger             │
         └─────────────────────────────────────────────┘
```

### Scaling Strategy

| Component | Scaling Trigger | Max Replicas |
|-----------|-----------------|--------------|
| Frontend | CPU > 70% | 20 |
| Backend API | RPS > 100/pod | 50 |
| Workers | Queue depth > 100 | 10 |
| Ollama | GPU Memory > 80% | N/A (Vertical) |
| ChromaDB | Query latency > 500ms | Cluster |
| PostgreSQL | Connections > 80% | Read Replicas |

## Multi-Tenant Isolation

```
Organization A                    Organization B
┌─────────────────────┐           ┌─────────────────────┐
│ Users               │           │ Users               │
│ Documents           │           │ Documents           │
│ Knowledge Bases     │           │ Knowledge Bases     │
│ Conversations       │           │ Conversations       │
│ Vectors (ChromaDB)  │           │ Vectors (ChromaDB)  │
│                     │           │                     │
│ Filter: org_id=xxx  │           │ Filter: org_id=yyy  │
└─────────────────────┘           └─────────────────────┘
         │                                 │
         └──────────────┬──────────────────┘
                        ▼
            ┌─────────────────────┐
            │   Shared Infra      │
            │   (App, DB, Ollama) │
            └─────────────────────┘
```

- **Database**: Row-level security via `organization_id` foreign keys
- **Vector Store**: Separate collections per KB per organization
- **API**: All queries auto-filtered by user's organization
- **Quotas**: Per-organization limits enforced at service layer

## Observability Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TELEMETRY COLLECTION                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Metrics   │  │   Traces    │  │    Logs     │         │
│  │ Prometheus  │  │ OpenTelemetry│ │ Structured  │         │
│  │  (Pull)     │  │  (OTLP)      │  │  (JSON)     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    STORAGE & QUERY                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ Prometheus  │  │   Jaeger    │  │    Loki     │         │
│  │  (Metrics)  │  │  (Traces)   │  │   (Logs)    │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   VISUALIZATION & ALERTING                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Grafana    │  │  Jaeger UI  │  │  Grafana    │         │
│  │  Dashboards │  │  (Traces)   │  │  (Logs)     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
```

### Key Metrics Categories

| Category | Prefix | Examples |
|----------|--------|----------|
| HTTP | `http_` | requests_total, duration, in_flight |
| AI/ML | `ai_` | embedding_time, generation_time, token_count |
| Retrieval | `retrieval_` | search_time, rerank_time, bm25_time |
| Business | `chat_`, `documents_` | sessions_active, uploads, queries |
| Infrastructure | `cpu_`, `memory_`, `disk_` | usage, available, io |

## Disaster Recovery

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKUP STRATEGY                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │  Database   │  │  Vector DB  │  │   Config/   │         │
│  │  (Daily)    │  │  (Daily)    │  │   Secrets   │         │
│  │  Point-in-  │  │  Snapshots  │  │  (Git/Vault)│         │
│  │  Time Recovery│             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
       ┌────────────┐  ┌────────────┐  ┌────────────┐
       │   RPO: 1h  │  │   RTO: 4h  │  │  Multi-AZ  │
       │   RTO: 2h  │  │   RPO: 1h  │  │  Deployment│
       └────────────┘  └────────────┘  └────────────┘
```