# Security Hardening Documentation

This document describes the comprehensive security enhancements implemented for the Text Summarization Service.

## 🔒 Security Features Overview

### 1. JWT Validation with JWKS Support

**Implementation**: `auth.py`

- **JWKS Integration**: Downloads public keys from Auth Service's JWKS endpoint
- **Algorithm Support**: RS256 and ES256 (RSA and ECDSA signatures)
- **Key Caching**: Configurable TTL-based caching with automatic refresh
- **Comprehensive Validation**: Token signature, expiration, claims, and tenant validation
- **Error Handling**: Graceful fallback and detailed error logging

**Configuration**:
```env
AUTH_SERVICE_URL=http://auth-service:8080
JWKS_CACHE_TTL=3600
JWT_ALGORITHM=RS256
```

**Usage**:
```python
from auth import validate_jwt_token

# Validate token with tenant checking
payload = await validate_jwt_token(token, tenant_id="tenant-123")
```

### 2. Mutual TLS (mTLS) Support

**Implementation**: `tls_config.py`

- **Certificate Management**: Reads certificates from `/etc/certs` directory
- **Mutual Authentication**: Client certificate validation
- **Security Hardening**: Modern cipher suites, disabled legacy protocols
- **Certificate Validation**: Automatic certificate existence and readability checks
- **Context Creation**: Separate contexts for server and client connections

**Required Certificates**:
```
/etc/certs/
├── ca.crt          # Certificate Authority
├── server.crt      # Server certificate
├── server.key      # Server private key
├── client.crt      # Client certificate (for outbound connections)
└── client.key      # Client private key
```

**Configuration**:
```env
ENABLE_TLS=true
ENABLE_MUTUAL_TLS=true
TLS_CERTS_DIR=/etc/certs
```

### 3. Header Validation and Propagation

**Implementation**: `middleware.py`

- **X-Tenant-ID**: Validates tenant context for multi-tenancy
- **X-Request-ID**: Ensures request traceability (auto-generated if missing)
- **Format Validation**: Prevents injection attacks and malformed headers
- **Propagation**: Headers are added to responses for tracking
- **Logging Integration**: Structured logging with security context

**Security Headers Added**:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`
- `Content-Security-Policy: default-src 'self'; ...`

**Configuration**:
```env
REQUIRE_TENANT_ID=true
REQUIRE_REQUEST_ID=true
AUTO_GENERATE_REQUEST_ID=true
```

### 4. CI/CD Security Scanning

**Implementation**: `.github/workflows/ci.yml`

#### Security Scans Included:
1. **Bandit**: Python code security analysis
2. **Safety**: Dependency vulnerability scanning
3. **Trivy**: Docker image vulnerability scanning
4. **Code Quality**: Linting, formatting, and type checking

#### Pipeline Stages:
- **Security Scan**: Runs Bandit and Safety checks
- **Security Integration**: Tests TLS and JWT configurations
- **Docker Security**: Scans built images for vulnerabilities
- **Artifact Upload**: Stores security reports for review

**Configuration**: `.bandit`
```ini
[bandit]
exclude_dirs = ["/tests", "/venv"]
confidence = ["HIGH", "MEDIUM", "LOW"]
severity = ["HIGH", "MEDIUM", "LOW"]
```

## 🚀 Quick Start

### 1. Install Dependencies
```bash
make install
```

### 2. Generate Test Certificates
```bash
make generate-test-certs
```

### 3. Run Security Scans
```bash
make security-scan      # Basic scanning
make security-full      # Comprehensive analysis
```

### 4. Test Security Features
```bash
make test-security      # Test TLS and authentication
```

### 5. Start Service with TLS
```bash
# Development mode
TLS_CERTS_DIR=./test-certs make run

# Production mode
make run-prod
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

```bash
cp .env.example .env
# Edit .env with your configuration
```

### Key Security Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `ENABLE_TLS` | `true` | Enable TLS encryption |
| `ENABLE_MUTUAL_TLS` | `true` | Enable client certificate validation |
| `AUTH_SERVICE_URL` | `http://auth-service:8080` | Auth service for JWKS |
| `REQUIRE_TENANT_ID` | `true` | Require X-Tenant-ID header |
| `REQUIRE_REQUEST_ID` | `true` | Require X-Request-ID header |
| `RATE_LIMIT_CALLS` | `100` | Requests per period |
| `RATE_LIMIT_PERIOD` | `60` | Rate limiting period (seconds) |

## 🔍 Security Scanning

### Manual Security Checks

```bash
# Run all security scans
make security-full

# Individual scans
bandit -r . -f txt                    # Code security
safety check                         # Dependency vulnerabilities
docker run --rm trivy image myapp    # Container scanning
```

### Continuous Integration

The CI pipeline automatically runs:
- Code security analysis (Bandit)
- Dependency vulnerability checks (Safety)
- Docker image scanning (Trivy)
- Security integration tests

### Security Reports

Reports are generated in the `reports/` directory:
- `bandit-report.json`: Code security issues
- `safety-report.json`: Dependency vulnerabilities
- CI artifacts: Downloadable from GitHub Actions

## 🛡️ Security Best Practices

### 1. Certificate Management
- Use proper Certificate Authority in production
- Rotate certificates regularly (recommended: 90 days)
- Store private keys securely with restricted permissions
- Monitor certificate expiration dates

### 2. JWT Token Security
- Use RS256 or ES256 algorithms (avoid HS256 in distributed systems)
- Implement short token lifespans (15-30 minutes)
- Use refresh tokens for longer sessions
- Validate all claims including issuer, audience, and custom claims

### 3. Header Validation
- Always validate tenant context
- Use UUIDs for request IDs
- Log security events for monitoring
- Implement rate limiting per tenant

### 4. Network Security
- Use TLS 1.2+ only
- Implement mutual TLS for service-to-service communication
- Configure proper cipher suites
- Use secure headers in all responses

### 5. Monitoring and Alerting
- Monitor failed authentication attempts
- Alert on certificate expiration
- Track rate limiting violations
- Log security-relevant events

## 🚨 Security Incident Response

### 1. Authentication Failures
```python
# Check JWT validation logs
logger.error("JWT validation failed", token_id=token_id, client_ip=client_ip)
```

### 2. Certificate Issues
```python
# Monitor TLS configuration
tls_status = get_tls_config().get_tls_status()
if not tls_status["server_tls_available"]:
    alert_certificate_issue()
```

### 3. Rate Limiting Violations
```python
# Track rate limit violations
if not rate_limiter.is_allowed(client_ip):
    log_rate_limit_violation(client_ip)
```

## 📋 Security Checklist

### Pre-Deployment
- [ ] All security scans pass (Bandit, Safety, Trivy)
- [ ] TLS certificates are valid and properly configured
- [ ] JWT validation is working with Auth Service
- [ ] Headers are properly validated and propagated
- [ ] Rate limiting is configured appropriately
- [ ] Security headers are included in responses
- [ ] Secrets are not hardcoded in configuration
- [ ] Environment variables are properly set

### Production Setup
- [ ] TLS certificates from trusted CA
- [ ] Mutual TLS enabled for service-to-service communication
- [ ] Auth Service JWKS endpoint is accessible
- [ ] Security monitoring and alerting configured
- [ ] Regular security scanning scheduled
- [ ] Certificate rotation procedures in place
- [ ] Incident response procedures documented

### Regular Maintenance
- [ ] Update dependencies regularly
- [ ] Run security scans weekly
- [ ] Review security logs monthly
- [ ] Rotate certificates quarterly
- [ ] Update security policies annually

## 🔗 References

- [OWASP API Security Top 10](https://owasp.org/www-project-api-security/)
- [RFC 7517: JSON Web Key (JWK)](https://tools.ietf.org/html/rfc7517)
- [RFC 8446: The Transport Layer Security (TLS) Protocol Version 1.3](https://tools.ietf.org/html/rfc8446)
- [NIST Cybersecurity Framework](https://www.nist.gov/cybersecurity)

## 📞 Support

For security-related questions or issues:
- Review security logs: `/var/log/security/`
- Check health endpoint: `GET /healthz`
- Verify TLS status: Use `make test-security`
- Contact security team: security@example.com
