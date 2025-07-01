# AI Summarization Service Setup

This guide provides instructions on setting up and using the AI Summarization Service. The service provides AI-powered text summarization with semantic validation, JWT authentication, and comprehensive monitoring.

## Quick Start

### Prerequisites
- Python 3.9+
- Valid JWT token for authentication
- Docker (optional, for containerized deployment)

### Local Development Setup

```bash
# Clone the repository and navigate to the service
cd services/text-summarization

# Install dependencies
make install

# Run the service locally
make local-run
```

The service will be available at `http://localhost:8000`

## API Reference

### Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

### Authentication
All endpoints require JWT authentication via the `Authorization` header:
```
Authorization: Bearer YOUR_JWT_TOKEN
```

### Endpoints

#### POST /v1/summarize
Generate a summary of the provided text.

**Request Headers:**
- `Content-Type: application/json`
- `Authorization: Bearer TOKEN`
- `X-Tenant-ID: your-tenant-id` (required)
- `X-Request-ID: unique-request-id` (optional, auto-generated if not provided)

**Request Body:**
```json
{
  "text_blob": "Your text to summarize here...",
  "ai_model": "facebook/bart-large-cnn",
  "max_length": 150,
  "min_length": 50,
  "semantic_threshold": 0.7,
  "request_id": "unique-request-id",
  "user_id": "user-123",
  "tenant_id": "tenant-456"
}
```

**Response:**
```json
{
  "summary": "Generated summary text...",
  "model_used": "facebook/bart-large-cnn",
  "semantic_score": 0.85,
  "processing_time_ms": 1250,
  "request_id": "unique-request-id",
  "timestamp": "2024-12-30T10:00:00Z"
}
```

#### GET /healthz
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "dependencies": {
    "pipeline": "healthy",
    "sentence_transformer": "healthy",
    "local_model": "healthy"
  },
  "uptime_seconds": 3600
}
```

#### GET /metrics
Prometheus metrics endpoint (text/plain format).

#### GET /docs
Interactive API documentation (Swagger UI) - available in development mode.

#### GET /redoc
Alternative API documentation (ReDoc) - available in development mode.

## Usage Examples

### Example 1: Basic Summarization

```bash
curl -X POST "http://localhost:8000/v1/summarize" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id" \
  -d '{
    "text_blob": "Artificial intelligence (AI) is intelligence demonstrated by machines, in contrast to the natural intelligence displayed by humans and animals. Leading AI textbooks define the field as the study of intelligent agents: any device that perceives its environment and takes actions that maximize its chance of successfully achieving its goals.",
    "ai_model": "facebook/bart-large-cnn",
    "max_length": 100,
    "min_length": 30
  }'
```

### Example 2: Summarization with Custom Parameters

```bash
curl -X POST "http://localhost:8000/v1/summarize" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id" \
  -H "X-Request-ID: req-12345" \
  -d '{
    "text_blob": "Long article text here...",
    "ai_model": "facebook/bart-large-cnn",
    "max_length": 200,
    "min_length": 50,
    "semantic_threshold": 0.8,
    "user_id": "user-123",
    "tenant_id": "tenant-456"
  }'
```

### Example 3: Handling Large Texts

For large texts, create a JSON file:

```json
{
  "text_blob": "Very long article content here... (can be several paragraphs)",
  "ai_model": "facebook/bart-large-cnn",
  "max_length": 300,
  "min_length": 100,
  "semantic_threshold": 0.75
}
```

Then submit it:

```bash
curl -X POST "http://localhost:8000/v1/summarize" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "X-Tenant-ID: your-tenant-id" \
  --data-binary @large-text.json
```

### Example 4: Python Client

```python
import requests
import json

def summarize_text(text, token, tenant_id):
    url = "http://localhost:8000/v1/summarize"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": tenant_id
    }
    
    payload = {
        "text_blob": text,
        "ai_model": "facebook/bart-large-cnn",
        "max_length": 150,
        "min_length": 50,
        "semantic_threshold": 0.7
    }
    
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Usage
token = "your-jwt-token"
tenant_id = "your-tenant-id"
text = "Your text to summarize..."

result = summarize_text(text, token, tenant_id)
if result:
    print(f"Summary: {result['summary']}")
    print(f"Semantic Score: {result['semantic_score']}")
```

## Configuration

### Environment Variables

- `ENVIRONMENT`: `development` or `production`
- `DEBUG`: `true` or `false`
- `HOST`: Service host (default: `0.0.0.0`)
- `PORT`: Service port (default: `8000`)
- `LOG_LEVEL`: Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`)

### Security Configuration

- `ENABLE_TLS`: Enable TLS encryption
- `ENABLE_MUTUAL_TLS`: Enable mutual TLS authentication
- `RATE_LIMIT_CALLS`: Requests per period (default: 100)
- `RATE_LIMIT_PERIOD`: Rate limit period in seconds (default: 60)

## Monitoring

### Health Checks

The service provides comprehensive health checks:

```bash
curl http://localhost:8000/healthz
```

### Metrics

Prometheus metrics are available at:

```bash
curl http://localhost:8000/metrics
```

Key metrics include:
- `http_requests_total`: Total HTTP requests
- `summarizations_total`: Total summarization requests
- `semantic_similarity_score`: Semantic similarity scores
- `active_requests`: Currently active requests

## Error Handling

### Common Error Responses

**401 Unauthorized:**
```json
{
  "error_code": "INVALID_TOKEN",
  "error_message": "JWT token is invalid or expired"
}
```

**400 Bad Request (Semantic Threshold Not Met):**
```json
{
  "error_code": "SEMANTIC_THRESHOLD_NOT_MET",
  "error_message": "Generated summary does not meet semantic similarity threshold",
  "request_id": "req-12345"
}
```

**429 Too Many Requests:**
```json
{
  "error_code": "RATE_LIMIT_EXCEEDED",
  "error_message": "Rate limit exceeded. Please try again later."
}
```

**500 Internal Server Error:**
```json
{
  "error_code": "MODEL_ERROR",
  "error_message": "AI model processing failed",
  "request_id": "req-12345"
}
```

## Development

### Local Setup

```bash
# Install dependencies
make install

# Run tests
make test

# Run security scans
make security-scan

# Start service locally
make local-run
```

### API Documentation

When running in development mode (`DEBUG=true`), interactive API documentation is available:

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI JSON**: `http://localhost:8000/openapi.json`

These endpoints are disabled in production for security reasons.
