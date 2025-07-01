# MCP Context Service

A FastAPI-based context management service designed for multi-tenant environments with comprehensive security and observability features.

## Features

- **Multi-tenant Architecture**: Tenant-aware data isolation using PostgreSQL schemas
- **RESTful API**: Clean REST endpoints for context CRUD operations
- **Security**: JWT authentication with JWKS support, rate limiting, and comprehensive input validation
- **Observability**: Structured logging, Prometheus metrics, and OpenTelemetry integration
- **Data Validation**: Comprehensive input validation with Pydantic models
- **Caching Ready**: Prepared for Redis caching layer (future enhancement)

## API Endpoints

### Core Context Operations

- `POST /context` - Create new context data
- `GET /context/{id}` - Retrieve context by ID
- `PUT /context/{id}` - Update existing context

### System Endpoints

- `GET /healthz` - Health check with dependency status
- `GET /metrics` - Prometheus metrics
- `GET /` - Service information

## Authentication

The service uses JWT-based authentication with JWKS (JSON Web Key Set) support:

- **Bearer Token Required**: All context endpoints require a valid JWT token
- **Tenant Isolation**: Each request must include `X-Tenant-ID` header
- **Request Tracking**: `X-Request-ID` header for request tracing

## Data Model

### Context Structure

```json
{
  "id": "ctx_123e4567-e89b-12d3-a456-426614174000",
  "context_data": {
    "user_preferences": {
      "theme": "dark",
      "language": "en"
    }
  },
  "context_type": "user_preferences",
  "title": "User UI Preferences",
  "description": "User interface preferences and settings",
  "tags": ["ui", "preferences", "settings"],
  "tenant_id": "tenant-123",
  "user_id": "user-456",
  "created_at": "2024-01-15T08:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z",
  "expires_at": null,
  "version": 1
}
```

## Configuration

The service is configured via environment variables:

### Database Settings
- `DB_HOST` - PostgreSQL host (default: localhost)
- `DB_PORT` - PostgreSQL port (default: 5432)
- `DB_NAME` - Database name (default: context_service)
- `DB_USER` - Database username
- `DB_PASSWORD` - Database password

### Security Settings
- `JWT_SECRET_KEY` - JWT secret key (fallback for local dev)
- `AUTH_SERVICE_URL` - Auth service URL for JWKS (default: http://auth-service:8080)
- `ENABLE_TLS` - Enable TLS encryption (default: true)
- `REQUIRE_TENANT_ID` - Require X-Tenant-ID header (default: true)

### Service Settings
- `SERVICE_NAME` - Service name (default: mcp-context-service)
- `HOST` - Server host (default: 0.0.0.0)
- `PORT` - Server port (default: 8001)
- `ENVIRONMENT` - Environment (development/staging/production)
- `DEBUG` - Debug mode (default: false)

## Database Schema

The service uses tenant-aware PostgreSQL schemas:

- Each tenant gets a dedicated schema: `tenant_{tenant_id}`
- Automatic schema creation for new tenants
- Full-text search support with GIN indexes
- Automatic cleanup of expired contexts

### Schema Setup

```sql
-- Create tenant schema
SELECT create_tenant_schema('your_tenant_id');

-- Cleanup expired contexts
SELECT cleanup_expired_contexts('your_tenant_id');
```

## Deployment

### Docker

```bash
# Build image
docker build -t mcp-context-service .

# Run container
docker run -p 8001:8001 \
  -e DB_HOST=your-db-host \
  -e DB_PASSWORD=your-password \
  -e AUTH_SERVICE_URL=http://your-auth-service:8080 \
  mcp-context-service
```

### Environment Variables Example

```bash
# Database
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=context_service
export DB_USER=context_user
export DB_PASSWORD=secure_password

# Security
export AUTH_SERVICE_URL=http://auth-service:8080
export ENABLE_TLS=true
export REQUIRE_TENANT_ID=true

# Service
export ENVIRONMENT=production
export DEBUG=false
export LOG_LEVEL=INFO
```

## Development

### Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Initialize database schema
psql -d context_service -f schema.sql

# Run the service
python main.py
```

### Local Development Setup

#### Quick Start
```bash
# From project root - starts all services
make local-run

# Or run just context service
cd services/context-service && make local-run
```

#### Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=context_service
export DB_USER=context_service_user
export DB_PASSWORD=context_service_password
export AUTH_SERVICE_URL=http://localhost:8443
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=myroot

# Start the service
python main.py
```

### Complete API Flow Examples

#### 1. Authentication (Get JWT Token)
```bash
# First, get a JWT token from auth service
TOKEN=$(curl -s -X POST http://localhost:8443/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=demo_code&client_id=demo-client" \
  | jq -r '.access_token')
```

#### 2. Create Context Data
```bash
curl -X POST http://localhost:8001/context \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
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

**Expected Response:**
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
  "tenant_id": "demo-tenant",
  "created_at": "2024-01-15T08:00:00Z",
  "version": 1
}
```

#### 3. Retrieve Context Data
```bash
CONTEXT_ID="ctx_123e4567-e89b-12d3-a456-426614174000"

curl -X GET http://localhost:8001/context/$CONTEXT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: demo-tenant"
```

#### 4. Update Context Data
```bash
curl -X PUT http://localhost:8001/context/$CONTEXT_ID \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{
    "context_data": {
      "document_metadata": {
        "title": "Updated Project Requirements",
        "source": "confluence",
        "url": "https://company.atlassian.net/doc/123"
      },
      "user_preferences": {
        "summary_length": "long",
        "language": "en"
      }
    },
    "description": "Updated context for processing project documentation"
  }'
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=.

# Test health endpoint
curl http://localhost:8001/healthz

# Test with authentication
export TEST_TOKEN="your-jwt-token"
curl -X POST http://localhost:8001/context \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TEST_TOKEN" \
  -H "X-Tenant-ID: test-tenant" \
  -d '{
    "context_data": {"test": "data"},
    "context_type": "test_context"
  }'
```

## Monitoring and Observability

### Metrics

The service exposes Prometheus metrics at `/metrics`:

- Request counts and durations
- Context operation metrics
- Active request gauges
- Database operation metrics

### Logging

Structured logging with:

- Request/response logging
- Authentication events
- Database operations
- Error tracking with request IDs

### Health Checks

The `/healthz` endpoint provides:

- Service status
- Database connectivity
- Dependency health
- Service uptime

## Security Features

- **JWT Authentication**: JWKS-based token validation
- **Input Validation**: Comprehensive Pydantic validation
- **Rate Limiting**: Per-IP rate limiting
- **Security Headers**: OWASP-recommended security headers
- **Tenant Isolation**: Schema-based data separation
- **TLS Support**: Optional mutual TLS authentication

## Error Handling

Standardized error responses:

```json
{
  "error_code": "CONTEXT_NOT_FOUND",
  "error_message": "Context not found or expired",
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Future Enhancements

- Redis caching layer for improved performance
- Full-text search capabilities
- Context versioning and history
- Bulk operations support
- GraphQL API option
