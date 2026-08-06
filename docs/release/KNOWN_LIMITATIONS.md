# Known Limitations

## Overview

This document outlines known limitations in KifPilot AI Support Agent v1.0.0. These are documented to set appropriate expectations and guide future development.

---

## Functional Limitations

### RAG Pipeline

| Limitation | Impact | Workaround | Planned Fix |
|------------|--------|------------|-------------|
| **Single-turn context only** | Follow-up questions lose context beyond immediate history | Include relevant context in question | v1.1: Multi-turn context injection |
| **No table extraction** | Tables in PDFs/DOCX not parsed | Convert tables to text before upload | v1.2: Table extraction |
| **No image processing** | Images in documents ignored | Extract text manually | v1.3: OCR + vision models |
| **Fixed chunk size** | Suboptimal for some document types | Pre-process with custom chunking | v1.2: Configurable chunking |
| **No query classification** | All queries use same pipeline | Manual routing | v1.2: Query routing |

### Search & Retrieval

| Limitation | Impact | Workaround | Planned Fix |
|------------|--------|------------|-------------|
| **Single KB per query** | Can't search across KBs | Merge KBs or query separately | v1.1: Multi-KB search |
| **No semantic caching** | Repeated queries re-process | Manual caching | v1.2: Semantic cache |
| **BM25 index rebuild on restart** | Slow startup for large KBs | Keep ChromaDB running | v1.1: Persistent BM25 |
| **No federated search** | Can't search external sources | Manual aggregation | v1.3: Federated search |
| **Fixed RRF k=60** | Not optimal for all domains | N/A | v1.1: Configurable RRF |

### Streaming

| Limitation | Impact | Workaround | Planned Fix |
|------------|--------|------------|-------------|
| **No WebSocket support** | SSE only | Use SSE | v1.2: WebSocket |
| **No resumable streams** | Connection loss = restart | Client-side retry | v1.2: Resumable streams |
| **No stream compression** | High bandwidth for long responses | N/A | v1.2: Compression |
| **Single concurrent stream per user** | Can't parallelize | Queue requests | v1.2: Multi-stream |

### Document Processing

| Limitation | Impact | Workaround | Planned Fix |
|------------|--------|------------|-------------|
| **No password-protected PDFs** | Fails silently | Remove password | v1.1: Password handling |
| **No scanned PDF OCR** | Image-only PDFs fail | OCR externally | v1.2: Built-in OCR |
| **Limited metadata extraction** | Limited filtering | Add manually | v1.1: Enhanced metadata |
| **No version control** | Overwrites on re-upload | Manual versioning | v1.2: Document versions |
| **Max 50MB file size** | Large docs rejected | Split documents | v1.1: Configurable limit |

### Multi-tenancy

| Limitation | Impact | Workaround | Planned Fix |
|------------|--------|------------|-------------|
| **No cross-org sharing** | Can't share KBs/docs | Duplicate content | v1.2: Controlled sharing |
| **No org-level branding** | Uniform UI | Custom CSS | v1.2: White-labeling |
| **Single embedding model per org** | Can't optimize per KB | Single model | v1.2: Per-KB models |

---

## Technical Limitations

### Scalability

| Limitation | Current Limit | Planned Fix |
|------------|---------------|-------------|
| **Max documents per KB** | ~10,000 | v1.2: Sharding |
| **Max KBs per org** | 50 | v1.2: Increased limits |
| **Max concurrent streams** | 5/user | v1.2: Configurable |
| **Max KB size** | 10 GB | v1.2: Sharding |
| **Vector dimension fixed** | 768 (nomic-embed-text) | v1.2: Multi-model |
| **Single ChromaDB node** | No HA | v1.1: Cluster mode |

### Performance

| Limitation | Current Behavior | Planned Fix |
|------------|------------------|-------------|
| **Cold start latency** | ~3-5s first query | v1.1: Warmup |
| **No query result caching** | Every query executes | v1.2: Redis cache |
| **Sequential KB search** | Slow for many KBs | v1.1: Parallel search |
| **No query result pagination** | Full results returned | v1.1: Pagination |

### Reliability

| Limitation | Risk | Mitigation |
|------------|------|------------|
| **No automatic failover for Ollama** | GPU node failure = downtime | Multi-GPU nodes |
| **ChromaDB single-node** | Node failure = downtime | v1.1: Cluster mode |
| **No circuit breaker** | Cascading failures | v1.1: Resilience4j |
| **No dead letter queue** | Failed tasks lost | v1.1: DLQ |

---

## Platform Limitations

### Kubernetes
- Requires Kubernetes 1.28+
- Requires CSI driver for persistent volumes
- Requires NVIDIA device plugin for GPU
- No Windows node support

### Cloud Providers
- Tested on: AWS (EKS), GCP (GKE), Azure (AKS)
- Not tested on: On-prem (may work), other clouds
- GPU availability varies by region

### Browsers
- Supported: Chrome 110+, Firefox 110+, Safari 16+, Edge 110+
- Not supported: IE11, older versions
- Mobile: Responsive but not optimized

### Languages
- UI: English only
- Document processing: Best with English
- Embedding model: English-optimized (nomic-embed-text)
- RTL languages: Not tested

---

## Security Limitations

| Limitation | Description | Mitigation |
|------------|-------------|------------|
| **No SSO/SAML/OIDC** | Local auth only | v1.2: SSO support |
| **No SCIM provisioning** | Manual user mgmt | v1.2: SCIM |
| **No audit log streaming** | Local files only | v1.1: SIEM export |
| **No DLP** | Data loss prevention | v1.3: DLP |
| **No encryption key rotation UI** | Manual rotation | v1.2: Key mgmt UI |

---

## Operational Limitations

| Limitation | Impact |
|------------|--------|
| **No blue-green deployment UI** | CLI/ArgoCD only |
| **No feature flags** | All-or-nothing releases |
| **No A/B testing framework** | Manual comparison |
| **No chaos engineering integration** | Manual testing |
| **Limited cost attribution** | Per-org cost tracking |

---

## Deprecation Notices

| Feature | Deprecated In | Removed In | Replacement |
|---------|---------------|------------|-------------|
| `/api/v1/ollama/chat` | v1.0 | v2.0 | `/api/v1/chat/ask` |
| `vector_only` search type | v1.0 | v2.0 | `hybrid` with alpha=1.0 |
| `embedding_model` in KB create | v1.0 | v2.0 | Org-level default |

---

## Reporting Issues

If you encounter a limitation not listed here:
1. Check [GitHub Issues](https://github.com/kifpilot/ai-support-agent/issues)
2. Create new issue with `limitation` label
3. Include: version, environment, steps to reproduce, expected vs actual

---

## Feedback

We prioritize fixes based on user impact. Vote on GitHub issues to help prioritize!