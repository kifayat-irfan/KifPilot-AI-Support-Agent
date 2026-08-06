# Troubleshooting Guide

## Quick Reference

| Symptom | Likely Cause | First Check |
|---------|--------------|-------------|
| No search results | Documents not processed | Document status in UI |
| Slow responses | Large KB / no GPU | Ollama GPU status |
| Low confidence | Insufficient relevant docs | Add more documents |
| Upload fails | File type/size | Check 50MB limit, allowed types |
| Streaming stops | Client disconnect / timeout | Network, 5min timeout |
| High memory | Large model / many docs | Check Ollama models |

---

## Common Issues

### 1. Search Returns No Results

**Symptoms**: Query returns empty results or "No relevant documents found"

**Diagnosis**:
```bash
# Check document processing status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/documents?status=completed

# Check KB document count
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/knowledge-bases/{kb_id}/stats

# Check vector store collections
curl http://localhost:8000/api/v1/vector/collections
```

**Solutions**:
- Wait for document processing to complete (check status)
- Verify documents added to correct KB
- Check minimum score threshold (default 0.3, try 0.1)
- Ensure embedding model matches between upload and query

### 2. Slow Query Responses (>10s)

**Symptoms**: Chat/search takes too long

**Diagnosis**:
```bash
# Check Ollama GPU status
curl http://localhost:11434/api/tags

# Check retrieval metrics
curl http://localhost:8000/metrics | grep retrieval

# Check GPU memory
nvidia-smi
```

**Solutions**:
- Ensure Ollama uses GPU (check `nvidia-smi` shows Ollama process)
- Reduce `top_k` from 10 to 5
- Disable reranker if not critical
- Enable context compression
- Check ChromaDB persistence (use SSD)

### 3. Low Answer Confidence

**Symptoms**: AI says "I don't have enough information" or gives uncertain answers

**Diagnosis**:
```bash
# Check retrieval scores
curl -X POST http://localhost:8000/api/v1/retrieval/search \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "your question", "top_k": 10}'
```

**Solutions**:
- Add more relevant documents to KB
- Lower minimum score threshold (0.3 → 0.1)
- Increase `top_k` (5 → 10)
- Check document chunking quality (1000/200)
- Verify document content matches query domain

### 4. Document Upload Fails

**Symptoms**: 400/413/415 errors on upload

**Common Errors**:
| Error Code | Cause | Fix |
|------------|-------|-----|
| 400 | Empty file / validation | Check file not empty, valid format |
| 413 | File too large | Max 50MB, compress PDF |
| 415 | Unsupported type | Use PDF, DOCX, TXT, MD |
| 409 | Duplicate content | Use force_reindex=true |

**Validation Checklist**:
- File size < 50MB
- Extension: .pdf, .docx, .doc, .txt, .md, .csv, .json
- Not password protected
- Not corrupted
- No executable content

### 5. Streaming Chat Stops Unexpectedly

**Symptoms**: Response cuts off, no "complete" event

**Causes**:
- Client disconnect (network, tab close)
- 5-minute total timeout
- 30-second per-token timeout
- Ollama OOM / crash
- Client buffer issues

**Solutions**:
- Check browser Network tab for incomplete response
- Increase timeouts in nginx/proxy
- Monitor Ollama memory: `docker stats ollama`
- Implement client-side reconnection logic

### 6. High Memory Usage

**Symptoms**: OOM kills, slow performance

**Check**:
```bash
# Container memory
docker stats --no-stream

# Ollama models loaded
curl http://localhost:11434/api/ps

# ChromaDB memory
curl http://localhost:8000/api/v1/vector/collections
```

**Solutions**:
- Reduce `RERANKER_MAX_CANDIDATES` (20 → 10)
- Reduce `CHUNK_SIZE` (1000 → 500)
- Limit concurrent Ollama requests
- Use quantized models (q4_K_M)
- Enable context compression

---

## Service-Specific Issues

### Ollama Issues

```bash
# Check Ollama health
curl http://localhost:11434/api/tags

# Check model availability
curl http://localhost:11434/api/show -d '{"name": "qwen3.5:4b"}'

# Pull missing models
ollama pull qwen3.5:4b
ollama pull nomic-embed-text

# Check logs
docker logs ollama

# Restart Ollama
docker restart ollama
```

**Common Errors**:
| Error | Fix |
|-------|-----|
| "model not found" | `ollama pull model-name` |
| "CUDA out of memory" | Reduce batch size, use smaller model |
| "connection refused" | Check Ollama port 11434, firewall |
| "model loading timeout" | Increase timeout, check disk space |

### ChromaDB Issues

```bash
# Check collections
curl http://localhost:8000/api/v1/vector/collections

# Check collection count
curl http://localhost:8001/api/v1/collections

# Check persistence
ls -la /data/chroma_db

# Reset ChromaDB (dev only)
docker restart chromadb
```

**Common Errors**:
| Error | Fix |
|-------|-----|
| "collection not found" | Check KB creation, collection naming |
| "dimension mismatch" | Verify embedding model consistency |
| "disk full" | Clean old collections, increase disk |

### PostgreSQL Issues

```bash
# Check connection
psql $DATABASE_URL -c "SELECT 1"

# Check locks
psql $DATABASE_URL -c "SELECT * FROM pg_locks WHERE NOT granted;"

# Check long queries
psql $DATABASE_URL -c "SELECT * FROM pg_stat_activity WHERE state = 'active';"

# Vacuum
psql $DATABASE_URL -c "VACUUM ANALYZE;"
```

### Redis Issues

```bash
# Check connection
redis-cli ping

# Check memory
redis-cli info memory

# Check keys
redis-cli --scan --pattern "org:*"
```

---

## Error Codes Reference

| Code | HTTP | Description | Resolution |
|------|------|-------------|------------|
| `VALIDATION_ERROR` | 400 | Input validation failed | Check request format |
| `UNAUTHORIZED` | 401 | Invalid/expired token | Re-login |
| `FORBIDDEN` | 403 | Insufficient permissions | Check role/permissions |
| `NOT_FOUND` | 404 | Resource doesn't exist | Verify ID |
| `CONFLICT` | 409 | Duplicate resource | Use force_reindex |
| `FILE_TOO_LARGE` | 413 | Upload > 50MB | Compress file |
| `UNSUPPORTED_MEDIA_TYPE` | 415 | Invalid file type | Use allowed formats |
| `RATE_LIMITED` | 429 | Too many requests | Wait, implement backoff |
| `INTERNAL_ERROR` | 500 | Server error | Check logs |
| `SERVICE_UNAVAILABLE` | 503 | Dependency down | Check Ollama/ChromaDB |
| `STREAM_TIMEOUT` | 408 | Streaming timeout | Retry with shorter query |
| `GUARDRAILS_INPUT` | 400 | Input rejected | Rephrase question |
| `GUARDRAILS_OUTPUT` | 500 | Output rejected | Retry |

---

## Debugging Commands

### API Health Checks
```bash
# Overall health
curl http://localhost:8000/health

# Detailed health
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/health

# Ollama health
curl http://localhost:8000/api/v1/ollama/health

# Streaming health
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/v1/chat/stream/health
```

### Test Retrieval
```bash
# Vector search
curl -X POST http://localhost:8000/api/v1/retrieval/search \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "test", "top_k": 5}'

# Hybrid search
curl -X POST http://localhost:8000/api/v1/retrieval/hybrid-search \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "test", "top_k": 5, "use_rrf": true}'

# Rerank
curl -X POST http://localhost:8000/api/v1/retrieval/rerank \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "test", "documents": [{"id": "1", "text": "sample"}]}'
```

### Test RAG
```bash
# Non-streaming
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "What is the refund policy?", "top_k": 5}'

# Streaming
curl -X POST http://localhost:8000/api/v1/rag/stream \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "What is the refund policy?"}'
```

### Metrics
```bash
# Prometheus metrics
curl http://localhost:8000/metrics

# Key metrics
curl http://localhost:8000/metrics | grep -E "(http_request|retrieval|rag|ollama)"
```

---

## Log Analysis

### Key Log Patterns
```bash
# Search errors
grep -i "error" /var/log/kifpilot/app.log | tail -20

# Slow queries
grep "process_time_ms" /var/log/kifpilot/app.log | awk '$NF > 5000'

# Rate limits
grep "rate_limit_exceeded" /var/log/kifpilot/audit.log

# Guardrails
grep "guardrails" /var/log/kifpilot/app.log

# Streaming
grep "stream" /var/log/kifpilot/app.log
```

### Audit Log Queries
```bash
# Failed logins
grep "login_failed" audit.log | jq -r .ip_address | sort | uniq -c | sort -rn

# Permission denied
grep "permission_denied" audit.log | jq -r .user_id | sort | uniq -c | sort -rn

# Document deletions
grep "document_delete" audit.log | jq .

# Admin actions
grep "admin_" audit.log | jq .
```

---

## Escalation

### When to Escalate

| Severity | Criteria | Response Time |
|----------|----------|---------------|
| Critical | Service down, data loss | 15 min |
| High | Degraded performance, feature broken | 1 hour |
| Medium | Bug, minor issue | 4 hours |
| Low | Enhancement, question | Next sprint |

### Information to Provide

1. **Environment**: dev/staging/prod, version
2. **Steps to Reproduce**: Exact steps
3. **Expected vs Actual**: What should happen
4. **Logs**: Relevant log snippets
5. **Metrics**: Dashboard screenshots
6. **Recent Changes**: Deployments, config changes

### Runbook Links

- [Service Down Runbook](runbooks/service-down.md)
- [High Latency Runbook](runbooks/high-latency.md)
- [OOM Runbook](runbooks/oom.md)
- [Data Corruption Runbook](runbooks/data-corruption.md)