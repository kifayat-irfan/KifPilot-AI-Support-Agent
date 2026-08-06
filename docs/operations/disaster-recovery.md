# Disaster Recovery Guide

## Overview

Recovery procedures for various disaster scenarios with RTO/RPO targets.

## Recovery Targets

| Scenario | RTO | RPO | Priority |
|----------|-----|-----|----------|
| Single pod failure | 30s | 0 | Auto |
| Node failure | 2min | 0 | Auto |
| Zone failure | 15min | < 1hr | Manual |
| Region failure | 1hr | < 1hr | Manual |
| Data corruption | 4hr | < 1hr | Manual |
| Ransomware | 24hr | < 24hr | Manual |
| Complete loss | 4hr | < 1hr | Manual |

---

## Scenario 1: Pod/Container Failure

### Detection
- Kubernetes liveness/readiness probes
- Prometheus alert: `KubePodCrashLooping`

### Auto-Recovery
```yaml
# Deployment spec handles automatically
restartPolicy: Always
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

### Manual Steps (if needed)
```bash
# Check pod status
kubectl get pods -n kifpilot -l app=kifpilot-backend

# View logs
kubectl logs -n kifpilot -l app=kifpilot-backend --tail=100

# Force restart
kubectl delete pod -n kifpilot -l app=kifpilot-backend
```

---

## Scenario 2: Node Failure

### Detection
- Node status: NotReady
- Prometheus alert: `KubeNodeNotReady`

### Auto-Recovery
- Kubernetes reschedules pods (5 min default)
- PodDisruptionBudgets ensure availability

### Manual Steps
```bash
# Check node status
kubectl get nodes

# Cordon and drain (if not auto)
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Verify rescheduling
kubectl get pods -n kifpilot -o wide
```

---

## Scenario 3: Zone/Region Failure

### Detection
- Multiple nodes NotReady
- Cloud provider status page
- Prometheus: multiple node alerts

### Recovery Steps

#### Single Zone (Multi-AZ deployment)
```bash
# 1. Verify other zones healthy
kubectl get nodes -L topology.kubernetes.io/zone

# 2. Scale up in healthy zones
kubectl scale deployment kifpilot-backend --replicas=10 -n kifpilot

# 3. Verify traffic routing
kubectl get endpoints -n kifpilot
```

#### Full Region Failover
```bash
# 1. Activate DR region
kubectl config use-context dr-cluster

# 2. Scale up DR deployments
kubectl scale deployment kifpilot-backend --replicas=5 -n kifpilot
kubectl scale deployment kifpilot-frontend --replicas=3 -n kifpilot

# 3. Update DNS (Route53/CloudFlare)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456 \
  --change-batch file://failover-dns.json

# 4. Verify
curl -f https://api.example.com/health
```

---

## Scenario 4: Database Failure

### PostgreSQL Primary Failure

#### Detection
- Connection errors
- Prometheus: `pg_up == 0`

#### Auto-Failover (Patroni/Cloud SQL)
```bash
# Verify replica promoted
kubectl get pods -n data -l app=kifpilot-postgres

# Verify application reconnects
kubectl logs -n kifpilot deploy/kifpilot-backend | grep -i "database\|connection"
```

#### Manual Failover
```bash
# 1. Promote replica
kubectl exec -it postgres-replica-0 -n data -- patronictl failover --candidate postgres-replica-0

# 2. Update DNS/service
kubectl patch service kifpilot-postgres -n data -p '{"spec":{"selector":{"role":"master"}}}'

# 3. Verify
psql $DATABASE_URL -c "SELECT pg_is_in_recovery();"
```

### Restore from Backup
```bash
# 1. Stop application
kubectl scale deployment kifpilot-backend --replicas=0 -n kifpilot

# 2. Restore from latest backup
/scripts/restore-postgres.sh /backups/postgres/latest.sql.gz kifpilot

# 3. Replay WAL (if point-in-time)
# Configure recovery.signal with restore_command and target_time

# 4. Restart application
kubectl scale deployment kifpilot-backend --replicas=3 -n kifpilot
```

---

## Scenario 5: ChromaDB Failure

### Detection
- Vector search errors
- Prometheus: `chromadb_up == 0`

### Recovery
```bash
# 1. Check cluster status
kubectl get pods -n data -l app=chromadb

# 2. Restart if single node
kubectl delete pod -n data -l app=chromadb

# 3. If cluster, check consensus
kubectl exec -it chromadb-0 -n data -- chroma status

# 4. Restore from backup if corrupted
python /scripts/restore-chroma.py --backup-dir /backups/chroma --date $(date -d "yesterday" +%Y%m%d)
```

---

## Scenario 6: Ollama/GPU Failure

### Detection
- Generation timeouts
- Prometheus: `ollama_up == 0` or GPU memory errors

### Recovery
```bash
# 1. Check GPU status
kubectl get nodes -o custom-columns=NAME:.metadata.name,GPU:.status.allocatable.nvidia\.com/gpu

# 2. Check Ollama pods
kubectl get pods -n data -l app=ollama

# 3. Restart Ollama
kubectl delete pod -n data -l app=ollama

# 4. If GPU node down, reschedule
kubectl drain <gpu-node> --ignore-daemonsets --delete-emptydir-data
# Pods reschedule to other GPU nodes

# 5. Verify models loaded
curl http://ollama:11434/api/tags
```

---

## Scenario 7: Data Corruption

### Detection
- Checksum mismatches
- Application errors
- Audit log anomalies

### Recovery
```bash
# 1. Identify scope
# Check specific tables/collections
psql $DATABASE_URL -c "SELECT count(*) FROM documents WHERE content_hash IS NULL;"

# 2. Restore affected data
# Option A: Restore specific tables
pg_restore -t documents -t document_chunks /backups/postgres/latest.dump

# Option B: Full restore + WAL replay
/scripts/restore-postgres.sh /backups/postgres/20260115_020000.sql.gz kifpilot

# 3. Re-index ChromaDB
python -c "
import chromadb
client = chromadb.PersistentClient(path='/data/chroma_db')
for coll in client.list_collections():
    # ChromaDB auto-rebuilds on query
    coll.peek(1)
print('Re-index triggered')
"
```

---

## Scenario 8: Ransomware/Attack

### Detection
- Unexpected encryption
- Unauthorized access alerts
- Anomalous API usage

### Immediate Response
```bash
# 1. Isolate
kubectl annotate namespace kifpilot quarantine=true --overwrite
kubectl apply -f network-policies/deny-all.yaml -n kifpilot

# 2. Revoke all tokens
kubectl exec -it deploy/kifpilot-backend -n kifpilot -- \
  python -c "
from app.services.auth.service import AuthService
# Revoke all refresh tokens
"

# 3. Rotate secrets
kubectl create secret generic kifpilot-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -base64 32) \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -base64 32) \
  -n kifpilot --dry-run=client -o yaml | kubectl replace -f -

# 4. Restore from clean backup
# Follow full restore procedure

# 5. Forensic analysis
# Preserve logs, memory dumps, disk images
```

---

## Scenario 9: Complete Environment Loss

### Recovery Order
1. **Infrastructure**: Recreate cluster (Terraform)
2. **Data Layer**: Restore PostgreSQL, ChromaDB, Redis
3. **Config**: Apply Kubernetes manifests
4. **Secrets**: Restore from Vault
5. **Application**: Deploy via ArgoCD
6. **Verify**: Run smoke tests

### Estimated Timeline
| Step | Time |
|------|------|
| Cluster provisioning | 15 min |
| Data restore (PG) | 30 min |
| Data restore (ChromaDB) | 20 min |
| Config/App deploy | 10 min |
| Smoke tests | 5 min |
| **Total** | **~80 min** |

---

## Communication Plan

### Internal
| Severity | Channel | Template |
|----------|---------|----------|
| Critical | PagerDuty + Slack #incidents | "CRITICAL: [Service] down since [time]. Impact: [details]. ETA: [time]" |
| High | Slack #incidents | "HIGH: [Service] degraded. Impact: [details]. Investigating." |
| Medium | Slack #ops | "MEDIUM: [Issue] detected. Monitoring." |

### External (Status Page)
- Update status.example.com
- Email subscribers if > 30 min
- Social media if > 2 hours

---

## Post-Incident

### Required Actions
- [ ] Root cause analysis (RCA) within 48 hours
- [ ] Update runbooks
- [ ] Implement preventive measures
- [ ] Update monitoring/alerts
- [ ] Team retrospective

### RCA Template
```markdown
# Incident #[number] - [Title]

## Summary
- **Date**: 
- **Duration**: 
- **Impact**: 
- **Root Cause**: 

## Timeline
- HH:MM - Detection
- HH:MM - Escalation
- HH:MM - Mitigation
- HH:MM - Resolution

## Root Cause Analysis
[5 Whys analysis]

## Action Items
- [ ] Fix: [description] - Owner: @user - Due: YYYY-MM-DD
- [ ] Monitoring: [description] - Owner: @user - Due: YYYY-MM-DD
- [ ] Process: [description] - Owner: @user - Due: YYYY-MM-DD

## Lessons Learned
```

---

## DR Testing Schedule

| Test | Frequency | Scope |
|------|-----------|-------|
| Pod failure | Weekly (chaos) | Single service |
| Node failure | Monthly | Zone evacuation |
| Database failover | Monthly | Primary -> Replica |
| Zone failure | Quarterly | Multi-AZ |
| Region failover | Semi-annually | Full DR region |
| Ransomware simulation | Annually | Full isolation + restore |
| Complete loss | Annually | Full rebuild from backup |