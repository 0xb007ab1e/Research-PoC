# Text Summarization Service - Container Deployment

This directory contains the containerized version of the MCP Text Summarization Service with security hardening and Kubernetes manifests.

## Features

- **Multi-stage Docker build** using `python:3.11-slim` → `gcr.io/distroless/python3`
- **Security hardening**: Non-root user (UID 1000), read-only root filesystem, dropped capabilities
- **Kubernetes deployment** with Helm charts including resource limits and security contexts
- **Service mesh support** with Istio sidecar injection annotations
- **Network policies** for traffic control
- **Observability** with health checks, metrics, and OpenTelemetry integration

## Docker Build

Build the container image:

```bash
# Build with build arguments
docker build \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') \
  --build-arg VERSION=1.0.0 \
  --build-arg VCS_REF=$(git rev-parse HEAD) \
  -t gcr.io/your-project/text-summarization-service:1.0.0 .

# Push to registry
docker push gcr.io/your-project/text-summarization-service:1.0.0
```

## Security Features

### Dockerfile Security
- **Multi-stage build** to minimize attack surface
- **Distroless base image** (`gcr.io/distroless/python3`) with minimal packages
- **Non-root user** with UID 1000 as specified
- **Read-only root filesystem** (enforced at runtime)
- **No shell** or package managers in final image

### Kubernetes Security
- **Pod Security Context**: 
  - `runAsUser: 1000`
  - `runAsNonRoot: true`
  - `readOnlyRootFilesystem: true`
- **Security Context**:
  - All capabilities dropped
  - No privilege escalation
- **Network Policy**: Restricts ingress/egress traffic
- **Resource Limits**: CPU and memory constraints

## Helm Deployment

Deploy using Helm:

```bash
# Install the chart
helm install text-summarization ./helm/text-summarization \
  --set image.repository=gcr.io/your-project/text-summarization-service \
  --set image.tag=1.0.0

# Upgrade deployment
helm upgrade text-summarization ./helm/text-summarization \
  --set image.tag=1.1.0

# Uninstall
helm uninstall text-summarization
```

## Configuration

### Environment Variables

Key environment variables for the container:

```yaml
env:
  - name: ENVIRONMENT
    value: "production"
  - name: LOG_LEVEL
    value: "INFO"
  - name: LOG_FORMAT
    value: "json"
  - name: ENABLE_TELEMETRY
    value: "true"
  - name: OPENAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: ai-api-keys
        key: openai-key
```

### Service Mesh (Istio)

The deployment includes annotations for Istio sidecar injection:

```yaml
annotations:
  sidecar.istio.io/inject: "true"
  sidecar.istio.io/proxyCPU: "100m"
  sidecar.istio.io/proxyMemory: "128Mi"
```

### Custom Sidecars

Enable additional sidecars in `values.yaml`:

```yaml
sidecar:
  enabled: true
  name: "logging-agent"
  image: "fluent/fluent-bit:latest"
  resources:
    requests:
      cpu: 50m
      memory: 64Mi
```

## Resource Requirements

### Default Limits
- **CPU**: 200m limit, 100m request
- **Memory**: 256Mi limit, 128Mi request

### Scaling
For production workloads, consider:
- Increasing replica count: `replicaCount: 3`
- Horizontal Pod Autoscaler (HPA)
- Vertical Pod Autoscaler (VPA)

## Monitoring and Observability

### Health Checks
- **Liveness probe**: `/healthz` endpoint
- **Readiness probe**: `/healthz` endpoint
- **Startup probe**: 60s initial delay

### Metrics
- **Prometheus metrics**: `/metrics` endpoint
- **OpenTelemetry**: Distributed tracing enabled
- **Structured logging**: JSON format for log aggregation

### Security Scanning

The deployment supports:
- **Network segmentation** via NetworkPolicy
- **Pod Security Standards** compliance
- **Image vulnerability scanning** (configure in CI/CD)

## Local Development Setup

### Quick Start
```bash
# From project root - starts all services
make local-run

# Or run just text summarization service
cd services/text-summarization && make local-run
```

### Manual Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=text_summarization
export DB_USER=text_summarization_user
export DB_PASSWORD=text_summarization_password
export AUTH_SERVICE_URL=http://localhost:8443
export VAULT_ADDR=http://localhost:8200
export VAULT_TOKEN=myroot
export OPENAI_API_KEY=your-openai-key  # Optional for cloud models

# Start the service
python main.py
```

### Complete API Flow Examples

#### 1. Authentication (Get JWT Token)
```bash
# Generate PKCE challenge and get authorization code
python3 -c "
import base64, hashlib, secrets
verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode().rstrip('=')
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
print(f'Verifier: {verifier}')
print(f'Challenge: {challenge}')
"

# Exchange code for JWT token
TOKEN=$(curl -s -X POST http://localhost:8443/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=AUTHORIZATION_CODE&redirect_uri=http://localhost:3000/callback&client_id=demo-client&code_verifier=YOUR_VERIFIER" \
  | jq -r '.access_token')
```

#### 2. Create Context Data (Optional)
```bash
# Create context for document processing
CONTEXT_RESPONSE=$(curl -s -X POST http://localhost:8001/context \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{
    "context_data": {
      "document_metadata": {
        "title": "Project Requirements",
        "source": "confluence"
      },
      "user_preferences": {
        "summary_length": "medium",
        "language": "en"
      }
    },
    "context_type": "document_processing",
    "title": "Project Requirements Context"
  }')

CONTEXT_ID=$(echo $CONTEXT_RESPONSE | jq -r '.id')
echo "Created context: $CONTEXT_ID"
```

#### 3. Generate Text Summary
```bash
curl -X POST http://localhost:8000/v1/summarize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -H "X-Tenant-ID: demo-tenant" \
  -H "X-Request-ID: $(uuidgen)" \
  -d '{
    "text_blob": "This is a comprehensive project requirements document that outlines the key features, technical specifications, and implementation timeline for our new customer portal. The portal will serve as the primary interface for customers to access their account information, submit support tickets, and manage their subscription plans. Key features include single sign-on integration, real-time chat support, mobile responsiveness, and integration with our existing CRM system. The technical implementation will use React for the frontend, Node.js for the backend API, and PostgreSQL for data storage. The project timeline spans 6 months with major milestones at 2-month intervals.",
    "ai_model": "local",
    "summary_length": "medium",
    "summary_type": "extractive",
    "context_id": "'"$CONTEXT_ID"'",
    "tenant_id": "demo-tenant",
    "semantic_threshold": 0.7
  }'
```

**Expected Response:**
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

#### 4. Test Different AI Models
```bash
# Test with local model (default)
curl -X POST http://localhost:8000/v1/summarize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "text_blob": "Your text here...",
    "ai_model": "local",
    "summary_length": "short"
  }'

# Test with OpenAI (requires API key)
curl -X POST http://localhost:8000/v1/summarize \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "text_blob": "Your text here...",
    "ai_model": "openai",
    "summary_length": "medium"
  }'
```

### Development Testing

#### Health Checks
```bash
# Check service health
curl http://localhost:8000/healthz

# Check service info
curl http://localhost:8000/

# Check metrics
curl http://localhost:8000/metrics
```

#### Local Testing

Run the container locally:

```bash
# Run with docker
docker run -p 8000:8000 \
  -e ENVIRONMENT=development \
  -e LOG_LEVEL=DEBUG \
  gcr.io/your-project/text-summarization-service:1.0.0

# Test health endpoint
curl http://localhost:8000/healthz
```

### Security Testing

Validate security configurations:

```bash
# Check container runs as non-root
docker run --rm gcr.io/your-project/text-summarization-service:1.0.0 id

# Verify read-only filesystem (should fail)
kubectl exec -it deployment/text-summarization -- touch /test-file
```

## Troubleshooting

### Common Issues

1. **Permission denied errors**: Ensure UID 1000 has access to required files
2. **Startup failures**: Check resource limits and increase if needed
3. **Network issues**: Verify NetworkPolicy allows required traffic

### Debug Commands

```bash
# Check pod security context
kubectl get pod -o yaml | grep -A 10 securityContext

# View logs
kubectl logs deployment/text-summarization -f

# Exec into container (if debug shell available)
kubectl exec -it deployment/text-summarization -- /bin/sh
```
