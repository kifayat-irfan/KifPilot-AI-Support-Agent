# Security Checklist

## Pre-Deployment Security

### Infrastructure
- [ ] Kubernetes RBAC configured (least privilege)
- [ ] Network policies applied (deny by default)
- [ ] Pod Security Standards: Restricted
- [ ] Admission controllers: PodSecurityPolicy/OPA Gatekeeper
- [ ] Image vulnerability scanning in CI/CD
- [ ] Base images regularly updated
- [ ] Runtime security (Falco/sysdig) deployed

### Secrets Management
- [ ] No secrets in code/configmaps
- [ ] Secrets in Vault/Sealed Secrets/External Secrets Operator
- [ ] SECRET_KEY: 32+ chars, rotated quarterly
- [ ] Database passwords: 32+ chars, rotated quarterly
- [ ] API keys: Scoped, rotated per policy
- [ ] TLS certificates: cert-manager with Let's Encrypt
- [ ] mTLS between services (Istio/Linkerd)

### Network Security
- [ ] Ingress: TLS 1.2+ only, HSTS
- [ ] Egress: Restricted to required endpoints
- [ ] Service mesh: mTLS + authz policies
- [ ] WAF rules for OWASP Top 10
- [ ] DDoS protection (CloudFlare/AWS Shield)
- [ ] Private endpoints for databases

---

## Application Security

### Authentication
- [ ] JWT: HS256/RS256, 30min access, 7d refresh
- [ ] Password: bcrypt (12 rounds), min 12 chars
- [ ] MFA: TOTP for admin/manager roles
- [ ] Session management: Secure, HttpOnly, SameSite
- [ ] Rate limiting: Login (5/min), API (tiered)
- [ ] Account lockout: 5 failed attempts

### Authorization
- [ ] RBAC: 4 roles (Viewer, Editor, Manager, Admin)
- [ ] Permissions: 6 granular permissions
- [ ] Org-scoped: All queries filtered by org_id
- [ ] API: Permission checks on every endpoint
- [ ] UI: Role-based navigation/components

### Input Validation
- [ ] SQL injection: Parameterized queries only
- [ ] XSS: CSP headers, output encoding
- [ ] Command injection: No shell execution
- [ ] Path traversal: Canonicalize paths
- [ ] File upload: MIME + extension + magic bytes
- [ ] XXE: Disable external entities
- [ ] Deserialization: Safe libraries only

### Data Protection
- [ ] Encryption at rest: AES-256 (DB, ChromaDB, uploads)
- [ ] Encryption in transit: TLS 1.3 everywhere
- [ ] PII: Minimize collection, encrypt sensitive fields
- [ ] Data retention: Automated cleanup per policy
- [ ] Backup encryption: AES-256, separate keys

---

## API Security

### Headers
```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'
Strict-Transport-Security: max-age=31536000; includeSubDomains; preload
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: accelerometer=(), camera=(), geolocation=()
Cross-Origin-Embedder-Policy: require-corp
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Resource-Policy: same-origin
```

### Rate Limiting
| Tier | Requests/min | Requests/hour | Requests/day |
|------|--------------|---------------|--------------|
| Anonymous | 10 | 100 | 500 |
| Authenticated | 60 | 1000 | 10000 |
| Admin | 200 | 5000 | 50000 |
| Login | 5 | 20 | 100 |
| Upload | 5 | 50 | 200 |
| Streaming | 10 | 100 | 500 |

### CORS
- [ ] Specific origins only (no wildcards in prod)
- [ ] Credentials: true only for trusted origins
- [ ] Methods: GET, POST, PUT, PATCH, DELETE
- [ ] Headers: Authorization, Content-Type only

---

## File Upload Security

### Validation
- [ ] MIME type: Magic bytes verification
- [ ] Extension: Whitelist only
- [ ] Size: Max 50MB
- [ ] Executable detection: PE/ELF/Mach-O headers
- [ ] Zip bomb: Ratio + decompressed size limits
- [ ] Polyglot: Multi-format detection

### Storage
- [ ] Secure filenames: UUID + timestamp
- [ ] Virus scanning: ClamAV/Cloud AV
- [ ] Access control: Signed URLs, short TTL
- [ ] Encryption: SSE-S3 or customer keys

---

## Monitoring & Auditing

### Audit Logging
- [ ] Authentication events (login, logout, failed)
- [ ] Authorization events (permission denied)
- [ ] Data events (upload, delete, download)
- [ ] Admin actions (user mgmt, settings)
- [ ] Security events (rate limit, invalid input)
- [ ] Retention: 1 year minimum
- [ ] Immutable storage: WORM/S3 Object Lock

### Alerting
- [ ] Failed login burst (>5 in 15min)
- [ ] Permission denied spikes
- [ ] Rate limit exceeded
- [ ] Invalid input patterns
- [ ] Suspicious file uploads
- [ ] Privilege escalation attempts

---

## Compliance

### GDPR
- [ ] Data processing agreement
- [ ] Right to erasure: API + automated
- [ ] Data portability: Export API
- [ ] Consent management
- [ ] DPIA completed

### SOC 2
- [ ] Access controls documented
- [ ] Encryption verified
- [ ] Incident response tested
- [ ] Vendor assessments current

### Industry Standards
- [ ] OWASP ASVS Level 2
- [ ] NIST CSF aligned
- [ ] ISO 27001 controls mapped

---

## Incident Response

### Playbooks
- [ ] Service down
- [ ] Data breach
- [ ] Credential compromise
- [ ] DDoS attack
- [ ] Ransomware
- [ ] Insider threat

### Testing
- [ ] Penetration test: Annual
- [ ] Vulnerability scan: Weekly
- [ ] Red team exercise: Annual
- [ ] Phishing simulation: Quarterly
- [ ] Tabletop exercise: Quarterly

---

## Vendor Security

### Assessment
- [ ] Cloud provider: SOC 2, ISO 27001
- [ ] Ollama: Model supply chain verified
- [ ] ChromaDB: Supply chain verified
- [ ] Dependencies: SCA scanning

### Contracts
- [ ] DPA with all processors
- [ ] Security incident notification: 24h
- [ ] Right to audit
- [ ] Termination: Data return/destruction

---

## Security Checklist by Role

### Developers
- [ ] Secure coding training (annual)
- [ ] Code review: Security checklist
- [ ] Dependency updates: Automated + manual
- [ ] Secrets scanning: Pre-commit + CI

### DevOps
- [ ] Infrastructure as Code: Reviewed
- [ ] Kubernetes hardening: CIS benchmarks
- [ ] Backup encryption verified
- [ ] Disaster recovery tested

### Security Team
- [ ] Threat modeling: New features
- [ ] Incident response: < 1hr MTTR
- [ ] Vulnerability management: < 24h critical
- [ ] Security training: All staff annual