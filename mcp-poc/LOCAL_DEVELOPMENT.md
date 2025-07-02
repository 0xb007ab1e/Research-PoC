# MCP Platform - Local Development Environment

⬅️ **[Back to Main Documentation](./README.md)**

This document describes how to set up and run the MCP (Multi-Context Platform) services locally for development.

> 📖 **See Also:** [Main README](./README.md) • [CHANGELOG](./CHANGELOG.md) • [Dependency Management](./DEPENDENCY-MANAGEMENT.md)

## Overview

The MCP platform consists of three main services:
- **auth-service** (Go) - Authentication and authorization service
- **context-service** (Python/FastAPI) - Context data management service  
- **text-summarization** (Python/FastAPI) - Text processing and summarization service

## Prerequisites

### Required Software
- **Docker** (20.10+) and **Docker Compose** (2.0+)
- **Python** (3.11+) for Python services
- **Go** (1.21+) for auth-service
- **Make** for running build scripts

### Optional Software (for enhanced development experience)
- **air** for Go hot reloading: `go install github.com/cosmtrek/air@latest`
- **uvicorn** for Python hot reloading (installed via requirements)

## Quick Start

### 1. Start the Development Stack

The development stack includes all required dependencies:

```bash
make local-stack-up
```

This starts:
- **PostgreSQL** (localhost:5432) with separate databases for each service
- **HashiCorp Vault** (http://localhost:8200) in development mode
- **Redis** (localhost:6379) for caching (optional)
- **JWKS Mock Server** (http://localhost:8080) for JWT validation
- **Adminer** (http://localhost:8081) for database management

### 2. Start All Services

```bash
make local-run
```

This will:
1. Ensure the development stack is running
2. Start auth-service (Go) with hot-reload on port 8443
3. Start context-service (Python) with hot-reload on port 8001
4. Start text-summarization (Python) with hot-reload on port 8000

### 3. Verify Services

Check that all services are running:

```bash
# Check auth-service
curl http://localhost:8443/health

# Check context-service  
curl http://localhost:8001/healthz

# Check text-summarization
curl http://localhost:8000/healthz
```

## Development Stack Details

### PostgreSQL Configuration
- **Host:** localhost:5432
- **Admin User:** mcp_user / mcp_password
- **Databases:** 
  - `context_service` (user: context_service_user / context_service_password)
  - `text_summarization` (user: text_summarization_user / text_summarization_password) 
  - `auth_service` (user: auth_service_user / auth_service_password)

### HashiCorp Vault (Development Mode)
- **URL:** http://localhost:8200
- **Root Token:** myroot
- **Note:** Development mode only - data is NOT persisted

### Redis Configuration
- **Host:** localhost:6379
- **Password:** redis_password
- **Database assignments:**
  - Database 0: context-service
  - Database 1: text-summarization  
  - Database 2: auth-service

### JWKS Mock Server
- **URL:** http://localhost:8080/.well-known/jwks.json
- **Purpose:** Provides mock JWT keys for development
- **Note:** Development only - use real auth service in production

## Individual Service Development

### Running Individual Services

Each service can be run independently:

```bash
# Auth service (Go)
cd services/text-summarization/auth-service
make local-run

# Context service (Python)
cd services/context-service  
make local-run

# Text summarization service (Python)
cd services/text-summarization
make local-run
```

### Service-Specific Environment Variables

Each service's `local-run` target automatically exports these environment variables:

#### Common Variables (all services)
```bash
DB_HOST=localhost
DB_PORT=5432
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=myroot
ENVIRONMENT=development
DEBUG=true
```

#### Service-Specific Variables
```bash
# Context Service
DB_NAME=context_service
DB_USER=context_service_user
DB_PASSWORD=context_service_password
AUTH_SERVICE_URL=http://localhost:8080
REDIS_URL=redis://:redis_password@localhost:6379/0
PORT=8001

# Text Summarization Service  
DB_NAME=text_summarization
DB_USER=text_summarization_user
DB_PASSWORD=text_summarization_password
AUTH_SERVICE_URL=http://localhost:8080
REDIS_URL=redis://:redis_password@localhost:6379/1
PORT=8000

# Auth Service
DB_NAME=auth_service
DB_USER=auth_service_user  
DB_PASSWORD=auth_service_password
REDIS_URL=redis://:redis_password@localhost:6379/2
PORT=8443
```

## Hot Reloading

### Python Services (FastAPI)
Both Python services use `uvicorn --reload` for automatic code reloading:
- File changes trigger automatic service restarts
- No need to manually restart during development

### Go Service (auth-service)
The auth-service uses **air** for hot reloading if available:
- Install air: `go install github.com/cosmtrek/air@latest`
- Configuration in `.air.toml`
- Falls back to standard build if air is not available

## Development Stack Management

### Useful Commands

```bash
# Check stack status
make local-stack-status

# View stack logs
make local-stack-logs

# Stop the stack
make local-stack-down

# Restart the stack
make local-stack-down && make local-stack-up
```

### Database Management

Access databases via Adminer:
1. Open http://localhost:8081
2. Use PostgreSQL credentials from above
3. Or connect directly: `psql -h localhost -U mcp_user -d mcp_dev`

### Vault Development

Access Vault UI:
1. Open http://localhost:8200
2. Use token: `myroot`
3. Or CLI: `export VAULT_ADDR=http://localhost:8200 && vault auth -method=token token=myroot`

## Troubleshooting

### Common Issues

#### Port Conflicts
If ports are already in use, modify `docker-compose.dev.yml`:
```yaml
ports:
  - "15432:5432"  # Change PostgreSQL port
  - "18200:8200"  # Change Vault port
  # etc.
```

#### Services Not Starting
1. Check if development stack is running: `make local-stack-status`
2. Check logs: `make local-stack-logs`
3. Restart stack: `make local-stack-down && make local-stack-up`

#### Database Connection Issues
1. Verify PostgreSQL is running: `docker ps | grep postgres`
2. Test connection: `psql -h localhost -U mcp_user -d mcp_dev`
3. Check service-specific database exists: `\l` in psql

#### Permission Issues
```bash
# Make scripts executable
chmod +x scripts/postgres-init/01-init-databases.sh

# Fix Docker socket permissions (if needed)
sudo chmod 666 /var/run/docker.sock
```

### Service-Specific Debugging

#### Context Service
```bash
cd services/context-service
make test          # Run tests
make lint          # Check code quality
make security-scan # Security analysis
```

#### Text Summarization Service  
```bash
cd services/text-summarization
make test          # Run tests
make security-full # Comprehensive security scan
make lint          # Check code quality
```

#### Auth Service
```bash
cd services/text-summarization/auth-service
make test          # Run tests
make lint          # Run Go linter
go mod tidy        # Clean dependencies
```

## Testing the Complete Setup

### 1. Health Checks
```bash
# Check all services
curl http://localhost:8443/health
curl http://localhost:8001/healthz  
curl http://localhost:8000/healthz

# Check dependencies
curl http://localhost:8200/v1/sys/health
curl http://localhost:8080/.well-known/jwks.json
```

### 2. Integration Testing
```bash
# Run platform integration tests
cd tests
python -m pytest . -v
```

### 3. API Testing
```bash
# Test context service
curl -X POST http://localhost:8001/context \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: test-tenant" \
  -d '{"context_data": {"test": "data"}, "context_type": "test"}'

# Test text summarization
curl -X POST http://localhost:8000/summarize \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test document for summarization."}'
```

## Environment File Templates

For persistent environment configuration, create `.env` files in each service directory:

### services/context-service/.env
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=context_service
DB_USER=context_service_user
DB_PASSWORD=context_service_password
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=myroot
ENVIRONMENT=development
DEBUG=true
```

### services/text-summarization/.env
```bash
DB_HOST=localhost
DB_PORT=5432
DB_NAME=text_summarization
DB_USER=text_summarization_user
DB_PASSWORD=text_summarization_password
VAULT_ADDR=http://localhost:8200
VAULT_TOKEN=myroot
ENVIRONMENT=development
DEBUG=true
```

## Next Steps

1. **API Documentation:** Generate API docs with `make generate-docs`
2. **Security Testing:** Run `make security-scan` for each service
3. **Integration Tests:** Add service integration tests in `tests/`
4. **Monitoring:** Add Prometheus/Grafana stack for observability
5. **Production Setup:** Configure production deployment with Helm charts

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review individual service READMEs
3. Check Docker and service logs
4. Ensure all prerequisites are installed
