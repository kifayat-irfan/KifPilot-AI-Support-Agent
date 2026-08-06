# Upgrade Guide

## Overview

This guide covers upgrading KifPilot AI Support Agent between versions.

## Version Compatibility

| From Version | To Version | Migration Required |
|--------------|------------|-------------------|
| - | 1.0.0 | Fresh install |
| 1.0.x | 1.0.y | Rolling update |
| 1.x | 2.0 | Full migration |

---

## Pre-Upgrade Checklist

- [ ] Review release notes for breaking changes
- [ ] Test in staging environment
- [ ] Backup all data (PostgreSQL, ChromaDB, uploads, config)
- [ ] Verify backup integrity
- [ ] Schedule maintenance window
- [ ] Notify stakeholders
- [ ] Prepare rollback plan

---

## Backup Before Upgrade

```bash
# 1. PostgreSQL
pg_dump $DATABASE_URL | gzip > backup_postgres_$(date +%Y%m%d_%H%M%S).sql.gz

# 2. ChromaDB
python /scripts/backup-chroma.py --output /backups/chroma/pre-upgrade-$(date +%Y%m%d)

# 3. Uploads
rsync -av /app/uploads/ /backups/uploads/pre-upgrade-$(date +%Y%m%d)/

# 4. Configuration
kubectl get all -n kifpilot -o yaml > backup_k8s_$(date +%Y%m%d).yaml
kubectl get configmaps,secrets -n kifpilot -o yaml > backup_config_$(date +%Y%m%d).yaml
```

---

## Upgrade Procedures

### Patch Version (1.0.x → 1.0.y)

#### Rolling Update (Zero Downtime)

```bash
# 1. Update image tag in values.yaml or deployment
kubectl set image deployment/kifpilot-backend \
  backend=registry/kifpilot-backend:v1.0.y \
  -n kifpilot

# 2. Monitor rollout
kubectl rollout status deployment/kifpilot-backend -n kifpilot --timeout=10m

# 3. Verify
curl -f https://api.example.com/health/ready
curl -f https://api.example.com/api/v1/health
```

#### Frontend
```bash
# Update frontend
kubectl set image deployment/kifpilot-frontend \
  frontend=registry/kifpilot-frontend:v1.0.y \
  -n kifpilot

kubectl rollout status deployment/kifpilot-frontend -n kifpilot
```

### Minor Version (1.x → 1.y)

#### Database Migrations
```bash
# 1. Backup first!
# 2. Run migrations
kubectl exec -it deploy/kifpilot-backend -n kifpilot -- alembic upgrade head

# 3. Verify
kubectl exec -it deploy/kifpilot-backend -n kifpilot -- alembic current
```

#### Configuration Changes
```bash
# Review ConfigMap changes
kubectl diff -f configmap.yaml

# Apply
kubectl apply -f configmap.yaml

# Restart pods to pick up config
kubectl rollout restart deployment/kifpilot-backend -n kifpilot
```

### Major Version (1.x → 2.0)

**Requires full migration** - see [v2.0 Migration Guide](./MIGRATION_v2.0.md)

---

## Component-Specific Upgrades

### PostgreSQL
```bash
# 1. Backup
pg_dump $DATABASE_URL | gzip > pg_backup_$(date +%Y%m%d).sql.gz

# 2. Upgrade (using pg_upgrade for in-place)
# Or dump/restore for major version
pg_restore -d $NEW_DATABASE_URL backup.dump

# 3. Update connection string in ConfigMap
kubectl patch configmap kifpilot-config -n kifpilot \
  --patch '{"data":{"DATABASE_URL":"postgresql+asyncpg://..."}}'

# 4. Restart
kubectl rollout restart deployment/kifpilot-backend -n kifpilot
```

### Ollama
```bash
# 1. Pull new models
ollama pull qwen3.5:4b
ollama pull nomic-embed-text

# 2. Update Ollama image
kubectl set image statefulset/kifpilot-ollama \
  ollama=ollama/ollama:latest -n data

# 3. Rolling restart
kubectl rollout restart statefulset/kifpilot-ollama -n data

# 4. Verify models
curl http://ollama:11434/api/tags
```

### ChromaDB
```bash
# 1. Backup collections
python /scripts/backup-chroma.py --output /backups/chroma/pre-upgrade

# 2. Update image
kubectl set image statefulset/chromadb \
  chromadb=chromadb/chroma:0.4.xx -n data

# 4. Rolling restart
kubectl rollout restart statefulset/chromadb -n data

# 5. Verify
kubectl exec -it chromadb-0 -n data -- chroma status
```

### Redis
```bash
# 1. Save
redis-cli save

# 2. Update image
kubectl set image statefulset/redis \
  redis=redis:7.x-alpine -n data

# 3. Rolling restart
kubectl rollout restart statefulset/redis -n data
```

---

## Post-Upgrade Verification

### Health Checks
```bash
# API health
curl -f https://api.example.com/health
curl -f https://api.example.com/api/v1/health

# Ollama
curl -f https://api.example.com/api/v1/ollama/health

# Streaming
curl -f https://api.example.com/api/v1/chat/stream/health
```

### Functional Tests
```bash
# 1. Authentication
curl -X POST https://api.example.com/api/v1/auth/login \
  -d '{"email":"test@test.com","password":"password"}'

# 2. Document upload
curl -X POST https://api.example.com/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@test.pdf"

# 3. Search
curl -X POST https://api.example.com/api/v1/retrieval/search \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query":"test","top_k":5}'

# 5. Chat (non-streaming)
curl -X POST https://api.example.com/api/v1/chat/ask \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question":"Hello","top_k":3}'

# 6. Chat (streaming)
curl -N -X POST https://api.example.com/api/v1/chat/stream \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"question":"Hello","top_k":3}'
```

### Monitoring Verification
- [ ] Prometheus scraping all targets
- [ ] Grafana dashboards showing data
- [ ] Jaeger receiving traces
- [ ] Loki collecting logs
- [ ] Alerts firing correctly

---

## Rollback Procedures

### Application Rollback
```bash
# Quick rollback
kubectl rollout undo deployment/kifpilot-backend -n kifpilot
kubectl rollout undo deployment/kifpilot-frontend -n kifpilot

# Specific revision
kubectl rollout undo deployment/kifpilot-backend -n kifpilot --to-revision=3

# ArgoCD rollback
argocd app rollback kifpilot <previous-revision>
```

### Database Rollback
```bash
# If migration was applied
kubectl exec -it deploy/kifpilot-backend -n kifpilot -- alembic downgrade -1

# Full restore from backup
gunzip -c backup_postgres_20260115_020000.sql.gz | psql $DATABASE_URL
```

### ChromaDB Rollback
```bash
# Restore from backup
python /scripts/restore-chroma.py \
  --backup-dir /backups/chroma/pre-upgrade \
  --date 20260115
```

### Full System Rollback
```bash
# 1. Stop application
kubectl scale deployment kifpilot-backend --replicas=0 -n kifpilot
kubectl scale deployment kifpilot-frontend --replicas=0 -n kifpilot

# 2. Restore all data
/scripts/restore-postgres.sh backup_postgres_20260115_020000.sql.gz kifpilot
python /scripts/restore-chroma.py --backup-dir /backups/chroma/pre-upgrade
rsync -av /backups/uploads/pre-upgrade/ /app/uploads/

# 3. Restore config
kubectl apply -f backup_k8s_20260115.yaml

# 4. Restart
kubectl scale deployment kifpilot-backend --replicas=3 -n kifpilot
kubectl scale deployment kifpilot-frontend --replicas=3 -n kifpilot
```

---

## Troubleshooting Upgrades

### Pod Stuck in Pending
```bash
kubectl describe pod <pod-name> -n kifpilot
# Check events for resource constraints, PVC issues
```

### Database Migration Fails
```bash
# Check migration status
kubectl exec -it deploy/kifpilot-backend -n kifpilot -- alembic current

# Fix and retry
kubectl exec -it deploy/kifpilot-backend -n kifpilot -- alembic upgrade head
```

### Health Checks Fail
```bash
# Check logs
kubectl logs -n kifpilot -l app=kifpilot-backend --tail=100

# Check dependencies
curl http://kifpilot-postgres:5432
curl http://kifpilot-chromadb:8000/api/v1/heartbeat
curl http://kifpilot-ollama:11434/api/tags
```

### ChromaDB Collection Issues
```bash
# Check collections
curl http://kifpilot-chromadb:8000/api/v1/collections

# Recreate if needed
python -c "
import chromadb
client = chromadb.HttpClient(host='kifpilot-chromadb', port=8000)
for coll in client.list_collections():
    client.delete_collection(coll.name)
"
```

---

## Post-Upgrade Monitoring

### First 24 Hours
- [ ] Error rate < 0.1%
- [ ] Latency p95 < baseline
- [ ] No new alerts
- [ ] All dashboards green
- [ ] Business metrics normal

### First Week
- [ ] No regressions in search quality
- [ ] No regressions in answer confidence
- [ ] Resource usage stable
- [ ] Cost within budget

---

## Support

- **Documentation**: https://docs.kifpilot.ai
- **Issues**: https://github.com/kifpilot/ai-support-agent/issues
- **Slack**: #kifpilot-support
- **Email**: support@kifpilot.ai