# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

**DO NOT** create a public GitHub issue for security vulnerabilities.

Instead, please email us at **security@kifpilot.ai** with:

1. **Description** of the vulnerability
2. **Steps to reproduce** (if applicable)
3. **Potential impact** assessment
4. **Suggested fix** (if you have one)

We will acknowledge receipt within 48 hours and provide a timeline for remediation.

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 5 business days
- **Fix Timeline**: Depends on severity (typically 30-90 days)
- **Disclosure**: Coordinated disclosure after fix is deployed

## Security Features

### Authentication & Authorization
- JWT-based authentication with configurable expiration
- Role-Based Access Control (RBAC) with 4 roles (Admin, Manager, Editor, Viewer)
- Permission-based authorization (6 granular permissions)
- Multi-tenant organization isolation
- Secure password hashing (bcrypt)

### Rate Limiting
- Tier-based limits (Anonymous: 10/min, Authenticated: 60/min, Admin: 200/min)
- Special endpoint limits (login: 5/min, upload: 5/min, streaming: 10/min)
- HTTP 429 with Retry-After headers

### Input Validation
- SQL injection detection and prevention
- XSS protection (script tags, event handlers, javascript: URLs)
- Command injection prevention
- Path traversal detection
- Request size limits (10MB default)

### File Upload Security
- MIME type validation (magic bytes + extension)
- Executable file detection (PE, ELF, Mach-O)
- Zip bomb protection (compression ratio, decompressed size limits)
- Secure filename generation (UUID + timestamp)
- Blocked extensions: .exe, .dll, .so, .bat, .cmd, .php, .jsp, .asp, etc.

### Security Headers
- Content-Security-Policy (strict)
- Strict-Transport-Security (HSTS)
- X-Frame-Options: DENY
- X-Content-Type-Options: nosniff
- Referrer-Policy: strict-origin-when-cross-origin
- Permissions-Policy: restrictive
- Cross-Origin policies (COEP, COOP, CORP)

### Secrets Management
- Environment variable loading
- Encryption at rest (AES-GCM)
- Automatic rotation support
- No-secrets logging policy
- API key hashing for storage

### Audit Logging
- Authentication events (login, logout, failed login, token refresh)
- Authorization events (permission denied, role changes)
- Document events (upload, delete, download, view, update)
- Organization events (create, update, delete, member changes)
- Admin actions (user management, settings changes)
- Security events (suspicious activity, rate limit exceeded, invalid input)
- Structured JSON logs with correlation IDs

### Abuse Protection
- Failed login blocking (5 attempts / 15 minutes)
- Large payload rejection (configurable, default 10MB)
- Concurrent streaming session limits
- Request throttling

## Security Configuration

### Required for Production

```env
APP_ENV=production
SECRET_KEY=<strong-random-key-min-32-chars>
DATABASE_URL=postgresql+asyncpg://user:pass@host/db
CORS_ORIGINS=["https://yourdomain.com"]
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Recommended

- Enable HTTPS/TLS termination at reverse proxy
- Use PostgreSQL with SSL
- Configure Ollama with authentication if exposed
- Set up log aggregation (ELK, Loki, etc.)
- Enable Prometheus metrics scraping
- Configure alerting for security events

## Dependency Security

We regularly scan dependencies for vulnerabilities:

```bash
# Python
pip install pip-audit
pip-audit

# Node.js
npm audit
```

## Security Checklist for Deployments

- [ ] Strong SECRET_KEY generated and stored securely
- [ ] Database credentials rotated and encrypted
- [ ] HTTPS enforced with valid certificates
- [ ] CORS origins restricted to known domains
- [ ] Rate limiting enabled and tuned
- [ ] Audit logging configured and monitored
- [ ] File upload validation enabled
- [ ] Security headers present on all responses
- [ ] Secrets rotated on schedule
- [ ] Vulnerability scanning in CI/CD
- [ ] Backup encryption enabled
- [ ] Incident response plan documented

## Disclosure Policy

We follow coordinated vulnerability disclosure:

1. Reporter submits vulnerability privately
2. We confirm and assess severity
3. We develop and test fix
4. We deploy fix to production
5. We publish security advisory
6. Credit given to reporter (if desired)

## Contact

Security Team: **security@kifpilot.ai**

For non-security issues, use [GitHub Issues](https://github.com/kifpilot/ai-support-agent/issues).