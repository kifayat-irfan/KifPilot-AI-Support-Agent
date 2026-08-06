# Maintenance Guide

## Overview

Routine maintenance procedures for KifPilot production environment.

## Daily Tasks

### Automated (Cron)
- [ ] Database backup (02:00 UTC)
- [ ] ChromaDB snapshot (02:30 UTC)
- [ ] Uploads rsync (03:00 UTC)
- [ ] Log rotation (04:00 UTC)
- [ ] Metrics retention cleanup (04:30 UTC)

### Manual Checks
- [ ] Health endpoints: All green
- [ ] Disk usage: < 80%
- [ ] Memory usage: < 85%
- [ ] CPU usage: < 80%
- [ ] Error rate: < 0.1%
- [ ] Queue depth: < 500
- [ ] Active streams: Normal range

---

## Weekly Tasks

### Database
- [ ] `VACUUM ANALYZE` on all tables
- [ ] Check index usage: `pg_stat_user_indexes`
- [ ] Check table bloat: `pgstattuple`
- [ ] Verify replication lag: < 1s
- [ ] Check long-running queries: `pg_stat_activity`
- [ ] Connection pool stats: PgBouncer metrics

### Vector Store
- [ ] ChromaDB collection counts
- [ ] HNSW index health
- [ ] Disk usage per collection
- [ ] Query latency trends

### LLM/Ollama
- [ ] GPU memory usage
- [ ] Model load status
- [ ] Generation latency trends
- [ ] Token throughput

### Cache
- [ ] Redis memory usage
- [ ] Hit/miss ratio > 90%
- [ ] Eviction rate
- [ ] Key expiration cleanup

### Logs
- [ ] Audit log integrity check
- [ ] Error rate trends
- [ ] Guardrails trigger rate
- [ ] Retention compliance

---

## Monthly Tasks

### Security
- [ ] Rotate API keys (external integrations)
- [ ] Review audit logs for anomalies
- [ ] Update vulnerability scanner
- [ ] Scan dependencies: `pip-audit`, `npm audit`
- [ ] Review IAM policies
- [ ] Rotate database passwords (if not auto)

### Performance
- [ ] Review p95 latency trends
- [ ] Identify slow queries
- [ ] Optimize slow endpoints
- [ ] Review HPA scaling events
- [ ] Cost optimization review

### Capacity Planning
- [ ] Disk growth projection
- [ ] Memory growth projection
- [ ] CPU growth projection
- [ ] Vector store growth
- [ ] Plan scaling events

### Documentation
- [ ] Update runbooks
- [ ] Update architecture diagrams
- [ ] Review and update runbooks
- [ ] Update API documentation

---

## Quarterly Tasks

### Disaster Recovery
- [ ] Full restore test (staging)
- [ ] Failover test (primary -> replica)
- [ ] Zone failure simulation
- [ ] Ransomware simulation
- [ ] RTO/RPO verification

### Security
- [ ] Penetration test
- [ ] Red team exercise
- [ ] Dependency audit
- [ ] Certificate renewal check
- [ ] Penetration test report review

### Architecture Review
- [ ] Scaling bottlenecks
- [ ] Cost optimization
- [ ] Technology refresh evaluation
- [ ] Technical debt assessment

---

## Annual Tasks

### Major Reviews
- [ ] Architecture redesign assessment
- [ ] Security audit (external)
- [ ] Compliance audit
- [ ] Vendor risk assessment
- [ ] Business continuity plan update

### Infrastructure
- [ ] Kubernetes version upgrade plan
- [ ] Database major version upgrade
- [ ] GPU hardware refresh
- [ ] Storage tier optimization

---

## Maintenance Windows

### Standard
- **When**: Sunday 02:00-04:00 UTC
- **Duration**: 2 hours max
- **Notification**: 48 hours advance
- **Rollback**: < 15 minutes

### Emergency
- **When**: As needed
- **Approval**: Team lead + security
- **Communication**: Immediate #incidents

### Pre-Maintenance Checklist
- [ ] Create maintenance issue
- [ ] Notify stakeholders (email + Slack)
- [ ] Update status page
- [ ] Verify backups recent
- [ ] Prepare rollback plan
- [ ] Team on-call confirmed

### Post-Maintenance Checklist
- [ ] Verify all health checks
- [ ] Run smoke tests
- [ ] Check error rates
- [ ] Verify monitoring
- [ ] Update status page
- [ ] Close maintenance issue
- [ ] Document any issues

---

## Upgrade Procedures

### Kubernetes
```bash
# 1. Review release notes
# 2. Test in staging
# 3. Drain nodes sequentially
kubectl cordon <node>
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data

# 4. Upgrade control plane
# 5. Upgrade worker nodes
# 6. Verify
kubectl get nodes
kubectl get pods -A
```

### PostgreSQL
```bash
# 1. Backup
pg_dump $DATABASE_URL > backup.sql.gz

# 2. Upgrade (using pg_upgrade or pg_dump/restore)
# 3. Test in staging
# 4. Schedule maintenance window
# 5. Execute upgrade
# 4. Verify
psql $DATABASE_URL -c "SELECT version();"
```

### Ollama
```bash
# 1. Pull new model
ollama pull qwen3.5:4b

# 2. Test in staging
# 3. Blue-green deploy
# 4. Switch traffic
# 4. Verify
curl http://ollama:11434/api/tags
```

### ChromaDB
```bash
# 1. Backup collections
python backup-chroma.py

# 2. Upgrade image
# 3. Rolling restart
kubectl rollout restart statefulset/chromadb -n data

# 4. Verify
kubectl exec -it chromadb-0 -n data -- chroma status
```

### Application
```bash
# 1. Build and test
docker build -t kifpilot-backend:v1.1.0 .
docker push registry/kifpilot-backend:v1.1.0

# 2. ArgoCD sync
argocd app sync kifpilot

# 3. Or manual
kubectl set image deployment/kifpilot-backend backend=registry/kifpilot-backend:v1.1.0 -n kifpilot

# 4. Verify rollout
kubectl rollout status deployment/kifpilot-backend -n kifpilot

# 5. Run smoke tests
curl -f https://api.example.com/health/ready
```

---

## Common Maintenance Commands

### Kubernetes
```bash
# Check pod status
kubectl get pods -n kifpilot -o wide

# View logs
kubectl logs -n kifpilot -l app=kifpilot-backend --tail=100 -f

# Restart deployment
kubectl rollout restart deployment/kifpilot-backend -n kifpilot

# Scale deployment
kubectl scale deployment kifpilot-backend --replicas=5 -n kifpilot

# Check resource usage
kubectl top pods -n kifpilot
kubectl top nodes
```

### Database
```bash
# Connect
psql $DATABASE_URL

# Check connections
SELECT count(*), state FROM pg_stat_activity GROUP BY state;

# Check locks
SELECT * FROM pg_locks WHERE NOT granted;

# Kill long query
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';

# Vacuum
VACUUM ANALYZE;
```

### ChromaDB
```bash
# List collections
curl http://localhost:8000/api/v1/vector/collections

# Get collection stats
curl http://localhost:8000/api/v1/vector/collections/{name}/stats

# Peek collection
curl http://localhost:8000/api/v1/vector/collections/{name}/peek
```

### Ollama
```bash
# List models
ollama list

# Pull model
ollama pull qwen3.5:4b

# Remove model
ollama rm old-model

# Check GPU
nvidia-smi
```

### Redis
```bash
# Info
redis-cli info memory
redis-cli info stats

# Keys
redis-cli --scan --pattern "org:*" | head -20

# Flush (careful!)
redis-cli flushdb
```

---

## Troubleshooting Maintenance Issues

### Stuck Pods
```bash
# Force delete
kubectl delete pod <pod-name> -n kifpilot --grace-period=0 --force

# Check events
kubectl describe pod <pod-name> -n kifpilot
```

### PVC Issues
```bash
# Check PVC status
kubectl get pvc -n kifpilot

# Force delete stuck PVC
kubectl patch pvc <pvc-name> -n kifpilot -p '{"metadata":{"finalizers":null}}'
```

### Certificate Renewal
```bash
# Check cert-manager
kubectl get certificates -A

# Force renewal
kubectl delete secret <tls-secret> -n kifpilot
# cert-manager will regenerate
```

### Node Issues
```bash
# Cordon/drain
kubectl cordon <node>
kubectl drain <node> --ignore-daemonsets --delete-emptydir-data

# Uncordon
kubectl uncordon <node>
```

---

## Documentation Updates

After each maintenance:
- [ ] Update runbooks with new procedures
- [ ] Update architecture diagrams
- [ ] Update known issues
- [ ] Update contact lists
- [ ] Archive old logs