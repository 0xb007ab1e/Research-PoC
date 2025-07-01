# MCP Platform (Multi-Context Platform) - MVP v0.1.0

A comprehensive microservices platform for text summarization, context management, and authentication with enterprise-grade security features.

## 🚀 Quick Start

The MCP Platform consists of three core services that work together to provide a complete text processing and context management solution:

- **Auth Service** (Go) - OAuth2.1 authentication with JWT signing via HashiCorp Vault
- **Context Service** (Python/FastAPI) - Multi-tenant context data management
- **Text Summarization Service** (Python/FastAPI) - AI-powered text summarization

### Prerequisites

- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Python** (3.11+) for Python services
- **Go** (1.21+) for auth-service
- **Make** for running build scripts

### One-Command Setup

```bash
# Start the complete platform (all services + dependencies)
make local-run
```

This command will:
1. Start PostgreSQL, Vault, Redis, and supporting services
2. Build and start all three core services with hot-reload
3. Set up all necessary environment variables
4. Initialize databases and security configurations

### Verify Installation

```bash
# Check auth service
curl http://localhost:8443/health

# Check context service  
curl http://localhost:8001/healthz

# Check text summarization service
curl http://localhost:8000/healthz
```

## 📋 Complete API Flow Examples

### 1. Authentication Flow (OAuth2.1 + PKCE)

#### Step 1: Get Authorization Code
```bash
# Generate PKCE challenge (using Python)
python3 -c "
import base64, hashlib, secrets
verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
print(f'Verifier: {verifier}')
print(f'Challenge: {challenge}')
"

# Use the challenge in authorization request
curl "http://localhost:8443/authorize?response_type=code&client_id=demo-client&redirect_uri=http://localhost:3000/callback&scope=openid+profile&state=xyz&code_challenge=YOUR_CHALLENGE&code_challenge_method=S256"
```

#### Step 2: Exchange Code for JWT Token
```bash
curl -X POST http://localhost:8443/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=AUTHORIZATION_CODE&redirect_uri=http://localhost:3000/callback&client_id=demo-client&code_verifier=YOUR_VERIFIER"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 86400,
  "refresh_token": "rt_1234567890abcdef",
  "scope": "openid profile"
}
```

### 2. Context Management Flow

#### Create Context Data
```bash
curl -X POST http://localhost:8001/context \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{
    "context_data": {
      "document_metadata": {
        "title": "Project Requirements",
        "source": "confluence",
        "url": "https://company.atlassian.net/doc/123"
      },
      "user_preferences": {
        "summary_length": "medium",
        "language": "en"
      }
    },
    "context_type": "document_processing",
    "title": "Project Requirements Context",
    "description": "Context for processing project documentation",
    "tags": ["project", "requirements", "documentation"]
  }'
```

**Response:**
```json
{
  "id": "ctx_123e4567-e89b-12d3-a456-426614174000",
  "context_data": {
    "document_metadata": {
      "title": "Project Requirements",
      "source": "confluence",
      "url": "https://company.atlassian.net/doc/123"
    },
    "user_preferences": {
      "summary_length": "medium",
      "language": "en"
    }
  },
  "context_type": "document_processing",
  "title": "Project Requirements Context",
  "description": "Context for processing project documentation",
  "tags": ["project", "requirements", "documentation"],
  "tenant_id": "demo-tenant",
  "created_at": "2024-01-15T08:00:00Z",
  "updated_at": "2024-01-15T08:00:00Z",
  "version": 1
}
```

#### Retrieve Context Data
```bash
curl -X GET http://localhost:8001/context/ctx_123e4567-e89b-12d3-a456-426614174000 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-ID: demo-tenant"
```

### 3. Text Summarization Flow

#### Generate Summary with Context
```bash
curl -X POST http://localhost:8000/v1/summarize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{
    "text_blob": "This is a comprehensive project requirements document that outlines the key features, technical specifications, and implementation timeline for our new customer portal. The portal will serve as the primary interface for customers to access their account information, submit support tickets, and manage their subscription plans. Key features include single sign-on integration, real-time chat support, mobile responsiveness, and integration with our existing CRM system. The technical implementation will use React for the frontend, Node.js for the backend API, and PostgreSQL for data storage. The project timeline spans 6 months with major milestones at 2-month intervals.",
    "ai_model": "local",
    "summary_length": "medium",
    "summary_type": "extractive",
    "context_id": "ctx_123e4567-e89b-12d3-a456-426614174000",
    "tenant_id": "demo-tenant",
    "semantic_threshold": 0.7
  }'
```

**Response:**
```json
{
  "request_id": "req_987fcdeb-51a2-43d1-b456-789012345678",
  "summary": "A comprehensive customer portal project featuring single sign-on, real-time chat, mobile responsiveness, and CRM integration. The 6-month timeline uses React frontend, Node.js backend, and PostgreSQL database with 2-month milestone intervals.",
  "model_used": "sentence-transformers/all-MiniLM-L6-v2",
  "summary_length": "medium",
  "summary_type": "extractive",
  "semantic_score": 0.85,
  "processing_time_ms": 1234,
  "context_used": true,
  "timestamp": "2024-01-15T08:05:00Z"
}
```

## 🔧 Local Development Setup

### Individual Service Development

Each service can be run independently for focused development:

```bash
# Run auth service only
cd services/text-summarization/auth-service && make local-run

# Run context service only
cd services/context-service && make local-run

# Run text summarization service only
cd services/text-summarization && make local-run
```

### Development Stack Management

```bash
# Start just the infrastructure (PostgreSQL, Vault, Redis)
make local-stack-up

# Check stack status
make local-stack-status

# View logs
make local-stack-logs

# Stop everything
make local-stack-down
```

### Environment Configuration

The platform uses environment-based configuration. Key variables:

#### Database Configuration
```bash
DB_HOST=localhost
DB_PORT=5432
# Service-specific databases are auto-created
```

#### Security Configuration
```bash
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=myroot
ENABLE_TLS=false  # Set to true for production
ENABLE_MUTUAL_TLS=false  # mTLS for service-to-service
```

#### Service Ports
- **Auth Service**: 8443
- **Context Service**: 8001  
- **Text Summarization**: 8000
- **PostgreSQL**: 5432
- **Vault**: 8200
- **Redis**: 6379

## 🛠️ Troubleshooting

### JWT Token Issues

#### Invalid Token Error
```json
{
  "error_code": "INVALID_TOKEN",
  "error_message": "Token signature verification failed"
}
```

**Solutions:**
1. Verify JWT token format: `Bearer <token>`
2. Check token expiration: tokens expire after 24 hours
3. Ensure JWKS endpoint is accessible: `curl http://localhost:8443/.well-known/jwks.json`
4. Verify Vault is running and accessible

#### Token Validation Steps
```bash
# 1. Check Vault status
curl http://localhost:8200/v1/sys/health

# 2. Verify JWKS endpoint
curl http://localhost:8443/.well-known/jwks.json

# 3. Decode JWT token (without verification)
echo "YOUR_JWT_TOKEN" | cut -d. -f2 | base64 -d 2>/dev/null | jq .

# 4. Test token introspection
curl -X POST http://localhost:8443/introspect \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "token=YOUR_JWT_TOKEN"
```

### mTLS Configuration Issues

#### Certificate Errors
```
SSL handshake failed: certificate verification failed
```

**Solutions:**
1. Generate development certificates:
   ```bash
   ./scripts/generate-certs.sh
   ```

2. Verify certificate files exist:
   ```bash
   ls -la ./certs/
   # Should show: ca.crt, server.crt, server.key, client.crt, client.key
   ```

3. Test mTLS connection:
   ```bash
   curl --cert ./certs/client.crt --key ./certs/client.key \
        --cacert ./certs/ca.crt \
        https://localhost:8443/health
   ```

#### mTLS Configuration Steps
```bash
# 1. Enable mTLS in environment
export ENABLE_TLS=true
export ENABLE_MUTUAL_TLS=true
export TLS_CERT_FILE=./certs/server.crt
export TLS_KEY_FILE=./certs/server.key
export CA_CERT_FILE=./certs/ca.crt

# 2. Restart services
make local-stack-down && make local-run

# 3. Test with mTLS client
curl --cert ./certs/client.crt --key ./certs/client.key \
     --cacert ./certs/ca.crt \
     -H "Authorization: Bearer YOUR_TOKEN" \
     https://localhost:8001/healthz
```

### Database Connection Issues

#### Connection Refused
```
Database connection failed: connection refused
```

**Solutions:**
1. Verify PostgreSQL is running:
   ```bash
   docker ps | grep postgres
   ```

2. Check database logs:
   ```bash
   make local-stack-logs | grep postgres
   ```

3. Test direct connection:
   ```bash
   psql -h localhost -U mcp_user -d mcp_dev
   ```

4. Verify service-specific databases exist:
   ```sql
   \l  -- List all databases
   -- Should show: context_service, text_summarization, auth_service
   ```

### Rate Limiting Issues

#### Too Many Requests
```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "error_message": "Rate limit exceeded. Please try again later."
}
```

**Solutions:**
1. Wait for rate limit window to reset (default: 60 seconds)
2. Adjust rate limits in configuration:
   ```bash
   export RATE_LIMIT_CALLS=200  # Increase from 100
   export RATE_LIMIT_PERIOD=60
   ```

### Service Discovery Issues

#### Service Unreachable
```
Connection failed: no route to host
```

**Solutions:**
1. Check all services are running:
   ```bash
   curl http://localhost:8443/health  # Auth
   curl http://localhost:8001/healthz # Context  
   curl http://localhost:8000/healthz # Summarization
   ```

2. Verify network connectivity:
   ```bash
   docker network ls
   docker network inspect mcp-poc_default
   ```

3. Check service logs:
   ```bash
   make local-stack-logs
   ```

## 📚 API Documentation

### Interactive Documentation
When running locally with debug mode enabled:

- **Text Summarization**: http://localhost:8000/docs (Swagger UI)
- **Context Service**: http://localhost:8001/docs (Swagger UI)
- **Auth Service**: Available via ReDoc at `/redoc` endpoints

### Generate API Documentation
```bash
# Generate comprehensive API documentation
make generate-docs

# View generated documentation
open docs/api/index.html
```

## 🔒 Security Features

- **OAuth2.1 with PKCE**: Modern authentication flow
- **JWT with RS256**: Cryptographically signed tokens via Vault
- **Mutual TLS (mTLS)**: Service-to-service encryption
- **Multi-tenant isolation**: Tenant-scoped data access
- **Rate limiting**: Per-IP request limiting
- **Input validation**: Comprehensive request validation
- **Security headers**: OWASP-recommended HTTP headers

## 📊 Monitoring & Observability

### Metrics Endpoints
- Auth Service: http://localhost:8443/metrics
- Context Service: http://localhost:8001/metrics  
- Text Summarization: http://localhost:8000/metrics

### Health Checks
```bash
# Comprehensive health check script
#!/bin/bash
services=("8443:auth" "8001:context" "8000:summarization")
for service in "${services[@]}"; do
  port="${service%%:*}"
  name="${service##*:}"
  status=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$port/health* 2>/dev/null)
  echo "$name service: $status"
done
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client App    │    │   Load Balancer │    │   Auth Service  │
│                 │◄──►│                 │◄──►│   (Port 8443)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                       │
                                ▼                       ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │ Context Service │    │  HashiCorp Vault│
                       │   (Port 8001)   │    │   (Port 8200)   │
                       └─────────────────┘    └─────────────────┘
                                │                       
                                ▼                       
                       ┌─────────────────┐    ┌─────────────────┐
                       │Text Summarization│    │   PostgreSQL    │
                       │   (Port 8000)   │◄──►│   (Port 5432)   │
                       └─────────────────┘    └─────────────────┘
```

## 🚀 Production Deployment

For production deployment, see:
- [GitOps Deployment Guide](./gitops/README.md)
- [Kubernetes Manifests](./k8s/)
- [Helm Charts](./charts/)
- [Security Documentation](./docs/security/08-security.md)

## 📖 Documentation Index

### 📋 Core Documentation
- [Local Development Guide](./LOCAL_DEVELOPMENT.md) - Complete setup and development workflow
- [Dependency Management](./DEPENDENCY-MANAGEMENT.md) - Dependency strategy and security scanning
- [CI/CD Pipeline Overview](./README-CICD.md) - Quick CI/CD reference
- [Version History](./CHANGELOG.md) - Detailed changelog and release notes

### 🔧 Service Documentation
- [Context Service](./services/context-service/README.md) - Multi-tenant context management
- [Text Summarization Service](./services/text-summarization/README.md) - AI-powered summarization
- [Auth Service](./services/text-summarization/auth-service/README.md) - OAuth2.1 authentication

### 🏗️ Infrastructure & Operations
- [GitOps Deployment](./gitops/README.md) - Production deployment strategies
- [Database Setup](./services/context-service/DATABASE_SETUP.md) - Database migration and bootstrap
- [Security Controls](./docs/security/08-security.md) - Comprehensive security documentation
- [CI/CD Pipeline Details](./docs/ci-cd-pipeline.md) - Detailed pipeline documentation

### 🧪 Testing & Quality
- [End-to-End Testing](./tests/e2e/README.md) - E2E test suite documentation
- [MVP Completion Summary](./docs/STEP15_MVP_COMPLETION.md) - Project completion status

## 🔄 Version History

See [CHANGELOG.md](./CHANGELOG.md) for detailed version history.

## 📄 License

This project is licensed under the MIT License. See individual service directories for specific licensing details.
