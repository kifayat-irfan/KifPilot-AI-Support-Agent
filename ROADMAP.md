# Roadmap

## Vision

Build the most capable, secure, and developer-friendly AI customer support platform that empowers organizations to deliver exceptional customer experiences through intelligent automation.

## Release Timeline

### v1.0.0 (Current) - Foundation ✅
- Multi-tenant architecture with RBAC
- Document processing pipeline
- Hybrid search (BM25 + Vector + RRF)
- Cross-encoder re-ranking
- Query expansion & context compression
- RAG with citations
- Streaming chat (SSE)
- Conversation memory
- Enterprise security (rate limiting, audit logging, input validation, secure uploads)
- Observability (Prometheus, OpenTelemetry, structured logging)
- React frontend with full feature parity
- Comprehensive test suite (unit, integration, load, regression)
- CI/CD pipeline

### v1.1.0 - Enhanced Intelligence (Q3 2026)
- [ ] **Advanced RAG Features**
  - [ ] Multi-hop reasoning for complex queries
  - [ ] Query decomposition and planning
  - [ ] Self-correction with reflection loops
  - [ ] Confidence calibration
- [ ] **Improved Retrieval**
  - [ ] ColBERT-style late interaction
  - [ ] Sparse embeddings (SPLADE) support
  - [ ] Metadata-aware filtering boost
  - [ ] Query-time boosting rules
- [ ] **Document Processing**
  - [ ] OCR support for scanned PDFs
  - [ ] Table extraction and structured data
  - [ ] Image captioning for visual content
  - [ ] Custom chunking strategies per doc type

### v1.2.0 - Platform Extensibility (Q4 2026)
- [ ] **Plugin System**
  - [ ] Custom retrieval plugins
  - [ ] Custom embedding providers
  - [ ] Custom LLM providers (OpenAI, Anthropic, etc.)
  - [ ] Webhook/event system
- [ ] **API Enhancements**
  - [ ] GraphQL endpoint
  - [ ] Batch operations API
  - [ ] Async job queue for long-running tasks
  - [ ] WebSocket support for real-time updates
- [ ] **Integrations**
  - [ ] Slack/Discord/Teams bots
  - [ ] Zendesk/Intercom connectors
  - [ ] Salesforce/HubSpot CRM sync
  - [ ] Custom webhook destinations

### v1.3.0 - Analytics & Intelligence (Q1 2027)
- [ ] **Analytics Dashboard**
  - [ ] Query analytics and trends
  - [ ] Document usage heatmaps
  - [ ] Citation quality metrics
  - [ ] User satisfaction tracking
- [ ] **Knowledge Management**
  - [ ] Automated gap detection
  - [ ] Content freshness scoring
  - [ ] Duplicate/near-duplicate detection
  - [ ] Smart tagging suggestions
- [ ] **A/B Testing Framework**
  - [ ] Prompt variation testing
  - [ ] Model comparison
  - [ ] Retrieval strategy comparison

### v2.0.0 - Enterprise Scale (Q2 2027)
- [ ] **Multi-Region Deployment**
  - [ ] Active-active geo-replication
  - [ ] Data residency controls
  - [ ] Cross-region failover
- [ ] **Advanced Security**
  - [ ] SSO/SAML/OIDC integration
  - [ ] SCIM provisioning
  - [ ] Audit log streaming (SIEM)
  - [ ] Data loss prevention (DLP)
- [ ] **Enterprise Features**
  - [ ] Custom SLA management
  - [ ] Advanced reporting & compliance
  - [ ] White-labeling support
  - [ ] Dedicated infrastructure option

## Technical Debt & Improvements

### Ongoing
- [ ] Increase test coverage to >90%
- [ ] Reduce p95 latency <200ms
- [ ] Optimize memory usage for large KBs
- [ ] Improve Ollama model switching
- [ ] Better error messages and recovery

### Architecture
- [ ] Event-driven architecture for document processing
- [ ] Separate read/write models (CQRS)
- [ ] Message queue for async operations
- [ ] Distributed tracing improvements
- [ ] Feature flags system

## Community Requests

High priority community requests (vote in discussions):

1. **Multi-language support** - Non-English document processing
2. **API rate limit tiers** - Per-customer configurable limits
3. **Custom prompt templates** - Per-KB prompt customization
4. **Export/Import** - Knowledge base portability
5. **Web UI for admin** - Full admin panel in frontend
6. **Mobile app** - React Native companion app

## Contributing to Roadmap

- Vote on [GitHub Discussions](https://github.com/kifpilot/ai-support-agent/discussions)
- Submit feature requests via [Issues](https://github.com/kifpilot/ai-support-agent/issues)
- Join monthly community calls (announced in discussions)
- Contribute implementations for prioritized items

## Maintenance

| Version | Release Date | End of Support |
|---------|--------------|----------------|
| 1.0.x   | Aug 2026     | Feb 2027       |
| 1.1.x   | Q3 2026      | Q1 2027        |
| 1.2.x   | Q4 2026      | Q2 2027        |
| 1.3.x   | Q1 2027      | Q3 2027        |
| 2.0.x   | Q2 2027      | Q2 2028        |

LTS versions receive security patches for 12 months after release.