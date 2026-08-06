# Backup & Restore Guide

## Overview

Comprehensive backup and restore procedures for all KifPilot data stores.

## Backup Strategy

| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| PostgreSQL | Daily + WAL | 30 days | pg_dump + WAL archiving |
| ChromaDB | Daily | 7 days | Snapshot export |
| Uploads | Daily | 30 days | rsync / S3 sync |
| Config/Secrets | On change | 1 year | Git / Vault |
| Ollama Models | On change | N/A | Model registry |

---

## PostgreSQL Backup

### Automated Daily Backup

```bash
#!/bin/bash
# backup-postgres.sh - Run daily via cron

set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/postgres"
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

# Full dump
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/kifpilot_$DATE.sql.gz

# Verify backup
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "Backup successful: kifpilot_$DATE.sql.gz"
else
    echo "Backup failed!"
    exit 1
fi

# Cleanup old backups
find $BACKUP_DIR -name "kifpilot_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# Upload to S3 (optional)
# aws s3 cp $BACKUP_DIR/kifpilot_$DATE.sql.gz s3://kifpilot-backups/postgres/
```

### Point-in-Time Recovery (WAL)

```bash
# Enable WAL archiving in postgresql.conf
wal_level = replica
archive_mode = on
archive_command = 'cp %p /backups/wal/%f'
max_wal_senders = 3
wal_keep_segments = 64

# Restore to specific timestamp
pg_basebackup -D /var/lib/postgresql/data -R -P
# Create recovery.signal with:
# restore_command = 'cp /backups/wal/%f %p'
# recovery_target_time = '2026-01-15 10:30:00'
```

### Restore PostgreSQL

```bash
#!/bin/bash
# restore-postgres.sh

BACKUP_FILE=$1
TARGET_DB=$2

if [ -z "$BACKUP_FILE" ] || [ -z "$TARGET_DB" ]; then
    echo "Usage: $0 <backup_file.sql.gz> <target_database>"
    exit 1
fi

# Terminate connections
psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TARGET_DB';"

# Drop and recreate
dropdb $TARGET_DB
createdb $TARGET_DB

# Restore
gunzip -c $BACKUP_FILE | psql -d $TARGET_DB

echo "Restore completed"
```

---

## ChromaDB Backup

### Export Collection

```python
# backup-chroma.py
import chromadb
import json
from pathlib import Path

client = chromadb.PersistentClient(path="/data/chroma_db")
backup_dir = Path("/backups/chroma")
backup_dir.mkdir(parents=True, exist_ok=True)

collections = client.list_collections()

for collection in collections:
    print(f"Backing up {collection.name}...")
    
    # Get all data in batches
    all_ids = []
    all_embeddings = []
    all_metadatas = []
    all_documents = []
    
    batch_size = 1000
    offset = 0
    
    while True:
        results = collection.get(
            limit=batch_size,
            offset=offset,
            include=["embeddings", "metadatas", "documents"]
        )
        
        if not results["ids"]:
            break
            
        all_ids.extend(results["ids"])
        all_embeddings.extend(results["embeddings"])
        all_metadatas.extend(results["metadatas"])
        all_documents.extend(results["documents"])
        
        offset += batch_size
        if len(results["ids"]) < batch_size:
            break
    
    # Save to JSON
    backup_data = {
        "collection_name": collection.name,
        "metadata": collection.metadata,
        "count": len(all_ids),
        "ids": all_ids,
        "embeddings": all_embeddings,
        "metadatas": all_metadatas,
        "documents": all_documents
    }
    
    with open(backup_dir / f"{collection.name}.json", "w") as f:
        json.dump(backup_data, f)
    
    print(f"  Saved {len(all_ids)} vectors")

print("ChromaDB backup complete")
```

### Restore ChromaDB

```python
# restore-chroma.py
import chromadb
import json
from pathlib import Path

client = chromadb.PersistentClient(path="/data/chroma_db")
backup_dir = Path("/backups/chroma")

for backup_file in backup_dir.glob("*.json"):
    print(f"Restoring {backup_file.name}...")
    
    with open(backup_file) as f:
        data = json.load(f)
    
    collection_name = data["collection_name"]
    
    # Delete existing if any
    try:
        client.delete_collection(collection_name)
    except:
        pass
    
    # Create new collection
    collection = client.create_collection(
        name=collection_name,
        metadata=data["metadata"]
    )
    
    # Restore in batches
    batch_size = 1000
    for i in range(0, len(data["ids"]), batch_size):
        end = min(i + batch_size, len(data["ids"]))
        collection.add(
            ids=data["ids"][i:end],
            embeddings=data["embeddings"][i:end],
            metadatas=data["metadatas"][i:end],
            documents=data["documents"][i:end]
        )
    
    print(f"  Restored {len(data['ids'])} vectors")

print("ChromaDB restore complete")
```

---

## Uploads Backup

```bash
#!/bin/bash
# backup-uploads.sh - Run daily

SOURCE="/app/uploads"
DEST="/backups/uploads"
RETENTION_DAYS=30

mkdir -p $DEST

# Incremental sync with rsync
rsync -av --delete \
  --exclude="*.tmp" \
  --exclude="*.partial" \
  $SOURCE/ $DEST/latest/

# Create dated snapshot
DATE=$(date +%Y%m%d)
cp -al $DEST/latest $DEST/$DATE

# Cleanup old snapshots
find $DEST -maxdepth 1 -type d -name "20*" -mtime +$RETENTION_DAYS -exec rm -rf {} \;
```

---

## Configuration Backup

```bash
#!/bin/bash
# backup-config.sh

BACKUP_DIR="/backups/config"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup Kubernetes manifests
kubectl get all -n kifpilot -o yaml > $BACKUP_DIR/k8s-resources_$DATE.yaml
kubectl get configmaps -n kifpilot -o yaml > $BACKUP_DIR/configmaps_$DATE.yaml
kubectl get secrets -n kifpilot -o yaml > $BACKUP_DIR/secrets_$DATE.yaml

# Backup Helm values
helm get values kifpilot -n kifpilot > $BACKUP_DIR/helm-values_$DATE.yaml

# Git commit (if using GitOps)
cd /path/to/gitops
git add -A
git commit -m "Config backup $DATE" || true
git push origin main
```

---

## Full System Backup Script

```bash
#!/bin/bash
# full-backup.sh - Run daily at 02:00 UTC

set -euo pipefail

LOG_FILE="/var/log/kifpilot/backup_$(date +%Y%m%d).log"
exec > >(tee -a $LOG_FILE) 2>&1

echo "=== Full Backup Started: $(date) ==="

# 1. PostgreSQL
echo "Backing up PostgreSQL..."
/scripts/backup-postgres.sh

# 2. ChromaDB
echo "Backing up ChromaDB..."
python /scripts/backup-chroma.py

# 3. Uploads
echo "Backing up uploads..."
/scripts/backup-uploads.sh

# 4. Configuration
echo "Backing up configuration..."
/scripts/backup-config.sh

# 5. Verify backups
echo "Verifying backups..."
/scripts/verify-backups.sh

echo "=== Full Backup Completed: $(date) ==="
```

---

## Restore Procedures

### Complete System Restore

```bash
#!/bin/bash
# full-restore.sh

# 1. Stop application
kubectl scale deployment kifpilot-backend --replicas=0 -n kifpilot
kubectl scale deployment kifpilot-frontend --replicas=0 -n kifpilot

# 2. Restore PostgreSQL
/scripts/restore-postgres.sh /backups/postgres/kifpilot_20260115_020000.sql.gz kifpilot

# 3. Restore ChromaDB
python /scripts/restore-chroma.py --backup-dir /backups/chroma --date 20260115

# 4. Restore uploads
rsync -av /backups/uploads/20260115/ /app/uploads/

# 5. Restore config
kubectl apply -f /backups/config/k8s-resources_20260115.yaml

# 6. Start application
kubectl scale deployment kifpilot-backend --replicas=3 -n kifpilot
kubectl scale deployment kifpilot-frontend --replicas=3 -n kifpilot

# 7. Verify
sleep 30
curl -f http://localhost:8000/health/ready
```

### Point-in-Time Recovery

```bash
# Restore to specific timestamp
# 1. Restore base backup
pg_basebackup -D /var/lib/postgresql/data -R -P

# 2. Create recovery.signal with:
cat > /var/lib/postgresql/data/recovery.signal <<EOF
restore_command = 'cp /backups/wal/%f %p'
recovery_target_time = '2026-01-15 10:30:00'
recovery_target_action = 'promote'
EOF

# 3. Start PostgreSQL
systemctl start postgresql
```

---

## Verification

```bash
#!/bin/bash
# verify-backups.sh

echo "Verifying backups..."

# Check PostgreSQL backup
LATEST_PG=$(ls -t /backups/postgres/kifpilot_*.sql.gz | head -1)
if [ -f "$LATEST_PG" ]; then
    echo "✓ PostgreSQL backup exists: $LATEST_PG"
    gunzip -t $LATEST_PG && echo "  Integrity OK" || echo "  CORRUPT!"
else
    echo "✗ No PostgreSQL backup found"
fi

# Check ChromaDB backup
CHROMA_COUNT=$(ls /backups/chroma/*.json 2>/dev/null | wc -l)
if [ $CHROMA_COUNT -gt 0 ]; then
    echo "✓ ChromaDB backups: $CHROMA_COUNT collections"
else
    echo "✗ No ChromaDB backups"
fi

# Check uploads
if [ -d "/backups/uploads/latest" ]; then
    UPLOAD_COUNT=$(find /backups/uploads/latest -type f | wc -l)
    echo "✓ Uploads backup: $UPLOAD_COUNT files"
else
    echo "✗ No uploads backup"
fi

# Check config backup
if [ -f "/backups/config/helm-values_$(date +%Y%m%d).yaml" ]; then
    echo "✓ Config backup exists"
else
    echo "✗ Config backup missing"
fi

echo "Verification complete"
```

---

## Disaster Recovery Testing

```bash
#!/bin/bash
# dr-test.sh - Run monthly

echo "=== Disaster Recovery Test ==="

# 1. Create test namespace
kubectl create namespace kifpilot-dr-test

# 2. Restore to test namespace
/scripts/full-restore.sh --namespace kifpilot-dr-test --date $(date -d "yesterday" +%Y%m%d)

# 3. Run smoke tests
kubectl run smoke-test --image=curlimages/curl -n kifpilot-dr-test -- \
  curl -f http://kifpilot-backend:8000/health/ready

# 4. Test RAG
kubectl run rag-test --image=python:3.12 -n kifpilot-dr-test -- \
  python -c "
import httpx
r = httpx.post('http://kifpilot-backend:8000/api/v1/rag/query',
  json={'question': 'test', 'top_k': 1},
  headers={'Authorization': 'Bearer test-token'})
assert r.status_code == 200
print('RAG OK')
"

# 5. Cleanup
kubectl delete namespace kifpilot-dr-test

echo "DR test completed successfully"
```

---

## Backup Monitoring

```yaml
# Prometheus alerts for backup monitoring
groups:
- name: backup-alerts
  rules:
  - alert: BackupFailed
    expr: backup_job_success == 0
    for: 1h
    labels:
      severity: critical
    annotations:
      summary: "Backup job failed"
      
  - alert: BackupOld
    expr: time() - backup_last_success_timestamp > 86400
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: "Backup older than 24 hours"
      
  - alert: BackupSizeAnomaly
    expr: abs(backup_size_bytes - backup_size_bytes offset 1d) / backup_size_bytes > 0.5
    for: 1h
    labels:
      severity: warning
    annotations:
      summary: "Backup size changed > 50%"
```