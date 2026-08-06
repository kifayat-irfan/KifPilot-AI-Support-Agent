# Production Deployment Checklist

## Pre-Deployment

### Infrastructure
- [ ] Kubernetes cluster provisioned (v1.28+)
- [ ] Node pools: CPU (general), GPU (ollama), Memory (chromadb)
- [ ] Storage classes: fast-ssd (PostgreSQL, ChromaDB), standard (uploads)
- [ ] Ingress controller installed (nginx)
- [ ] cert-manager installed for TLS
- [ ] External DNS configured
- [ ] Load balancer configured

### Security
- [ ] Network policies applied
- [ ] RBAC configured (least privilege)
- [ ] Secrets in Vault/Sealed Secrets (not plaintext)
- [ ] TLS certificates via cert-manager
- [ ] Pod security standards (restricted)
- [ ] Image scanning in CI/CD
- [ ] Runtime security (Falco/sysdig)

### Database
- [ ] PostgreSQL 16+ with pgvector
- [ ] Primary + read replica
- [ ] Automated backups + WAL archiving
- [ ] Connection pooling (PgBouncer)
- [ ] Monitoring: connections, locks, query performance

### Vector Store
- [ ] ChromaDB cluster mode (3+ nodes)
- [ ] Persistent volumes on fast SSD
- [ ] HNSW index configured
- [ ] Backup/restore tested

### LLM Infrastructure
- [ ] Ollama on GPU nodes (NVIDIA)
- [ ] Models pre-pulled (qwen3.5:4b, nomic-embed-text)
- [ ] Model cache persisted
- [ ] GPU resource limits set

### Caching
- [ ] Redis cluster (3+ nodes)
- [ ] Memory limits configured
- [ ] Eviction policy: allkeys-lru

### Monitoring
- [ ] Prometheus + Grafana
- [ ] Jaeger for tracing
- [ ] Loki for logs
- [ ] Alertmanager configured
- [ ] Dashboards imported
- [ ] Alerting rules active

### CI/CD
- [ ] ArgoCD/Flux for GitOps
- [ ] Image vulnerability scanning
- [ ] Automated testing in pipeline
- [ ] Canary deployments
- [ ] Rollback capability

---

## Deployment Steps

### 1. Prepare Secrets
```bash
# Generate strong secrets
SECRET_KEY=$(openssl rand -base64 32)
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Store in Vault/sealed-secrets
kubectl create secret generic kifpilot-secrets \
  --from-literal=SECRET_KEY="$SECRET_KEY" \
  --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
  -n kifpilot
```

### 2. Deploy Infrastructure
```bash
# Apply in order
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f database/
kubectl apply -f monitoring/
```

### 3. Deploy Application
```bash
# Deploy backend
kubectl apply -f backend/

# Deploy frontend
kubectl apply -f frontend/

# Verify
kubectl rollout status deployment/kifpilot-backend -n kifpilot
kubectl rollout status deployment/kifpilot-frontend -n kifpilot
```

### 4. Configure Ingress
```bash
kubectl apply -f ingress/
# Verify TLS
curl -I https://api.example.com/health
curl -I https://app.example.com
```

### 5. Run Migrations
```bash
kubectl exec -it deploy/kifpilot-backend -n kifpilot -- alembic upgrade head
```

### 6. Verify Deployment
```bash
# Health checks
curl https://api.example.com/health
curl https://api.example.com/api/v1/health
curl https://api.example.com/api/v1/ollama/health

# Test RAG
curl -X POST https://api.example.com/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question": "test", "top_k": 1}'
```

---

## Post-Deployment

### Smoke Tests
- [ ] Health endpoints return 200
- [ ] Authentication works (login/logout)
- [ ] Document upload/download
- [ ] KB creation and search
- [ ] Chat streaming works
- [ ] Citations display correctly
- [ ] Admin panel accessible

### Performance Validation
- [ ] API p95 < 500ms
- [ ] RAG p95 < 3s
- [ ] Streaming TTFT < 500ms
- [ ] No errors in logs

### Monitoring
- [ ] Prometheus scraping all targets
- [ ] Grafana dashboards showing data
- [ ] Jaeger receiving traces
- [ ] Loki collecting logs
- [ ] Alerts firing correctly

### Documentation
- [ ] Runbooks updated
- [ ] API docs published
- [ ] Runbook links in alerts

---

## Rollback Plan

```bash
# Quick rollback
kubectl rollout undo deployment/kifpilot-backend -n kifpilot
kubectl rollout undo deployment/kifpilot-frontend -n kifpilot

# Database rollback (if migration)
kubectl exec -it deploy/kifpilot-backend -n kifpilot -- alembic downgrade -1

# Full rollback to previous ArgoCD sync
argocd app rollback kifpilot <previous-revision>
```

---

## Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| DevOps Lead | | | |
| Security Lead | | | |
| Backend Lead | | | |
| Frontend Lead | | | |
| Product Owner | | | |

---

## Emergency Contacts

| Service | Contact | Escalation |
|---------|---------|------------|
| Kubernetes | @devops-oncall | PagerDuty |
| Database | @dba-oncall | PagerDuty |
| Security | @security-team | Slack #security-incidents |
| Product | @pm-oncall | Slack #product-oncall |