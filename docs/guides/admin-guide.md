# Administrator Guide

This guide covers administrative tasks for managing KifPilot AI Support Agent at the organization level.

## Table of Contents

1. [Organization Management](#organization-management)
2. [User Management](#user-management)
3. [Role-Based Access Control](#role-based-access-control)
4. [Document & KB Administration](#document--kb-administration)
5. [Security Configuration](#security-configuration)
6. [Monitoring & Auditing](#monitoring--auditing)
7. [Backup & Maintenance](#backup--maintenance)
8. [Troubleshooting](#troubleshooting)

---

## Organization Management

### Creating Organizations

Only system administrators can create organizations:

```bash
# Via API (requires admin token)
POST /api/v1/organizations
{
  "name": "Customer Organization",
  "slug": "customer-org",
  "description": "Support for Customer X"
}
```

### Organization Settings

Configure per-organization:

- **Name & Slug**: Unique identifier
- **Description**: Purpose and scope
- **Timezone**: For scheduling/reporting
- **Default Embedding Model**: For new KBs
- **Retention Policies**: Document/conversation TTL
- **Feature Flags**: Enable/disable features

### Organization Limits

Set quotas to prevent abuse:

| Limit | Default | Description |
|-------|---------|-------------|
| Max Documents | 10,000 | Per organization |
| Max KBs | 50 | Per organization |
| Max Conversations | 1,000 | Per organization |
| Max File Size | 50MB | Per upload |
| Daily Queries | 10,000 | Per organization |

---

## User Management

### Inviting Users

1. Navigate to **Organization → Members**
2. Click **Invite Member**
3. Enter email and select role
4. User receives invitation email
5. User accepts and sets password

### User Statuses

- **Active**: Can log in and use features
- **Inactive**: Cannot log in (preserves data)
- **Pending**: Invitation sent, not yet accepted
- **Suspended**: Temporarily blocked (admin action)

### Bulk Operations

- **CSV Import**: Bulk invite users
- **Role Assignment**: Bulk role changes
- **Deactivation**: Bulk deactivate departed users

### User Lifecycle

```
Pending → Active → Inactive/Suspended
                ↓
            Deleted (GDPR)
```

---

## Role-Based Access Control

### Permission Matrix

| Permission | Viewer | Editor | Manager | Admin |
|------------|--------|--------|---------|-------|
| CHAT | ✅ | ✅ | ✅ | ✅ |
| VIEW_SESSIONS | ✅ | ✅ | ✅ | ✅ |
| UPLOAD_DOCUMENTS | ❌ | ✅ | ✅ | ✅ |
| DELETE_DOCUMENTS | ❌ | ❌ | ✅ | ✅ |
| MANAGE_USERS | ❌ | ❌ | ✅ | ✅ |
| MANAGE_SETTINGS | ❌ | ❌ | ❌ | ✅ |

### Custom Roles (Advanced)

Create custom roles via API:

```json
POST /api/v1/roles
{
  "name": "custom_role",
  "permissions": ["CHAT", "UPLOAD_DOCUMENTS"],
  "description": "Custom chat + upload role"
}
```

### Role Assignment Best Practices

1. **Principle of Least Privilege**: Assign minimum required role
2. **Regular Audits**: Review roles quarterly
3. **Separation of Duties**: Don't combine Manager + Admin
4. **Documentation**: Document role purposes

---

## Document & KB Administration

### Document Moderation

- **Review Queue**: Flagged documents for review
- **Content Policy**: Define acceptable content
- **Automatic Scanning**: PII, secrets, malware detection

### Knowledge Base Governance

- **Ownership**: Assign KB owners
- **Review Cycles**: Scheduled content reviews
- **Archival**: Auto-archive stale KBs
- **Usage Analytics**: Track KB adoption

### Storage Management

Monitor storage per organization:

```sql
-- Check document storage
SELECT org_id, COUNT(*) as docs, SUM(file_size) as total_size
FROM documents
GROUP BY org_id;
```

### Cleanup Policies

Configure automatic cleanup:

- **Trash Retention**: 30 days (configurable)
- **Conversation Retention**: 90 days (configurable)
- **Log Retention**: 1 year (configurable)
- **Orphaned Vectors**: Weekly cleanup job

---

## Security Configuration

### Authentication Settings

Configure in `.env` or admin panel:

```env
# Password policy
MIN_PASSWORD_LENGTH=12
REQUIRE_UPPERCASE=true
REQUIRE_LOWERCASE=true
REQUIRE_NUMBERS=true
REQUIRE_SYMBOLS=true
PASSWORD_HISTORY=5

# Session
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
MAX_CONCURRENT_SESSIONS=5

# MFA
MFA_REQUIRED_FOR_ADMIN=true
MFA_REQUIRED_FOR_MANAGER=false
```

### Rate Limiting

Tune per organization:

```json
{
  "anonymous": { "rpm": 10, "rph": 100, "rpd": 500 },
  "authenticated": { "rpm": 60, "rph": 1000, "rpd": 10000 },
  "admin": { "rpm": 200, "rph": 5000, "rpd": 50000 },
  "endpoints": {
    "/auth/login": { "rpm": 5, "rph": 20 },
    "/documents/upload": { "rpm": 5, "rph": 50 }
  }
}
```

### CORS Configuration

```env
CORS_ORIGINS=["https://app.yourdomain.com", "https://admin.yourdomain.com"]
CORS_ALLOW_CREDENTIALS=true
```

### Security Headers

All responses include:

- CSP: Strict content security policy
- HSTS: HTTP Strict Transport Security
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: Restrictive

### Audit Logging

All admin actions are logged:

```json
{
  "event_type": "admin_user_create",
  "user_id": "admin-id",
  "target_user_id": "new-user-id",
  "organization_id": "org-id",
  "ip_address": "192.168.1.1",
  "timestamp": "2026-01-15T10:30:00Z"
}
```

View audit logs:
```bash
# Recent admin actions
GET /api/v1/admin/audit-logs?event_type=admin_*&limit=100
```

---

## Monitoring & Auditing

### Health Checks

Monitor these endpoints:

| Endpoint | Purpose |
|----------|---------|
| `/health` | Basic liveness |
| `/api/v1/health` | Detailed health |
| `/api/v1/ollama/health` | LLM service |
| `/api/v1/chat/stream/health` | Streaming |

### Key Metrics

Monitor in Prometheus/Grafana:

- **Request Rate**: `http_requests_total`
- **Latency**: `http_request_duration` (p50, p95, p99)
- **Error Rate**: `http_requests_total{status=~"5.."}`
- **Active Users**: `users_active`
- **Query Volume**: `search_queries_total`
- **Document Uploads**: `documents_uploaded`
- **Vector Store**: `chromadb_collections`, `chromadb_documents`
- **Ollama**: `ollama_models_loaded`, `ollama_memory_usage`

### Alerting Rules

```yaml
groups:
- name: kifpilot-alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"

  - alert: HighLatency
    expr: histogram_quantile(0.95, rate(http_request_duration_bucket[5m])) > 5
    for: 10m
    labels:
      severity: warning

  - alert: OllamaDown
    expr: up{job="ollama"} == 0
    for: 2m
    labels:
      severity: critical

  - alert: DiskSpaceLow
    expr: (disk_available_bytes / disk_total_bytes) < 0.1
    for: 5m
    labels:
      severity: warning
```

### Audit Log Analysis

Key audit events to monitor:

```bash
# Failed logins (potential brute force)
grep "login_failed" audit.log | jq -r .ip_address | sort | uniq -c | sort -rn

# Permission denied (potential unauthorized access)
grep "permission_denied" audit.log | jq -r .user_id | sort | uniq -c | sort -rn

# Admin actions
grep "admin_" audit.log | jq .

# Document deletions
grep "document_delete" audit.log | jq .
```

---

## Backup & Maintenance

### Backup Strategy

| Component | Frequency | Retention | Method |
|-----------|-----------|-----------|--------|
| Database | Daily | 30 days | pg_dump / SQLite backup |
| Vector Store | Daily | 7 days | ChromaDB snapshot |
| Uploads | Daily | 30 days | File sync (rsync/S3) |
| Config | On change | 1 year | Git / Config management |

### Automated Backups

```bash
#!/bin/bash
# backup.sh - Run daily via cron

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/kifpilot/$DATE"

mkdir -p $BACKUP_DIR

# Database
pg_dump $DATABASE_URL | gzip > $BACKUP_DIR/db.sql.gz

# Vector store
tar -czf $BACKUP_DIR/chroma.tar.gz /data/chroma_db

# Uploads
tar -czf $BACKUP_DIR/uploads.tar.gz /data/uploads

# Config
cp /app/.env $BACKUP_DIR/env.bak

# Cleanup old backups (keep 30 days)
find /backups/kifpilot -type d -mtime +30 -exec rm -rf {} \;
```

### Maintenance Windows

Schedule weekly maintenance:

1. **Sunday 02:00-04:00 UTC**
2. Database vacuum/analyze
2. Vector store optimization
3. Log rotation
4. Security updates
5. Dependency updates

### Database Maintenance

```sql
-- Run weekly
VACUUM ANALYZE;

-- Check index usage
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes
WHERE idx_scan = 0;

-- Check table bloat
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables
WHERE schemaname = 'public';
```

---

## Troubleshooting

### Common Issues

#### Users Can't Log In

1. Check Ollama health: `GET /api/v1/ollama/health`
2. Verify database connectivity
3. Check rate limits: `grep "rate_limit_exceeded" audit.log`
4. Verify JWT secret hasn't changed

#### Slow Queries

1. Check retrieval metrics: `retrieval_latency_ms`
2. Verify ChromaDB performance
3. Check Ollama embedding latency
4. Consider increasing `top_k` or adding indexes

#### Document Upload Fails

1. Check file type/size limits
2. Verify upload directory permissions
3. Check disk space: `df -h`
4. Review validation errors in logs

#### High Memory Usage

1. Check Ollama model memory: `ollama ps`
2. Reduce `CHUNK_SIZE` or `RERANKER_MAX_CANDIDATES`
3. Enable context compression
4. Consider model quantization

### Debug Commands

```bash
# Check service status
systemctl status kifpilot-backend
systemctl status ollama

# View logs
journalctl -u kifpilot-backend -f
tail -f /var/log/kifpilot/audit.log

# Database connectivity
psql $DATABASE_URL -c "SELECT 1"

# Ollama models
ollama list

# ChromaDB collections
curl http://localhost:8000/api/v1/vector/collections

# Test retrieval
curl -X POST http://localhost:8000/api/v1/retrieval/search \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "test", "top_k": 3}'
```

### Escalation Procedures

| Severity | Response Time | Escalation |
|----------|---------------|------------|
| Critical (down) | 15 min | Page on-call |
| High (degraded) | 1 hour | Notify team lead |
| Medium (bug) | 4 hours | Assign to sprint |
| Low (enhancement) | Next sprint | Backlog |

---

## Appendix: Useful Queries

### Organization Stats
```sql
SELECT
  o.name as organization,
  COUNT(DISTINCT u.id) as users,
  COUNT(DISTINCT d.id) as documents,
  COUNT(DISTINCT kb.id) as knowledge_bases,
  COUNT(DISTINCT c.id) as conversations
FROM organizations o
LEFT JOIN users u ON u.organization_id = o.id
LEFT JOIN documents d ON d.organization_id = o.id
LEFT JOIN knowledge_bases kb ON kb.organization_id = o.id
LEFT JOIN conversations c ON c.organization_id = o.id
GROUP BY o.id, o.name;
```

### User Activity
```sql
SELECT
  u.email,
  u.last_login,
  COUNT(DISTINCT c.id) as conversations,
  COUNT(DISTINCT m.id) as messages
FROM users u
LEFT JOIN conversations c ON c.user_id = u.id
LEFT JOIN messages m ON m.conversation_id = c.id
WHERE u.organization_id = 'org-id'
GROUP BY u.id, u.email, u.last_login
ORDER BY u.last_login DESC;
```