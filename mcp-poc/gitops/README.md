# MCP Platform GitOps Configuration

This directory contains the GitOps configuration for the MCP (Model Context Protocol) platform services using ArgoCD for continuous deployment.

## Architecture Overview

### Services Managed
- **text-summarization**: Core text summarization service (Python/FastAPI)
- **auth-service**: Authentication and authorization service (Go)
- **context-service**: Context management and vector storage service (Python/FastAPI)

### Security Features
All Helm charts include the following security hardening:
- **Non-root containers**: All containers run as non-root user (UID 1000)
- **Read-only root filesystem**: Prevents runtime file system modifications
- **Dropped capabilities**: All Linux capabilities are dropped for minimal attack surface
- **Security contexts**: Pod and container-level security contexts enforced
- **Network policies**: Ingress/egress traffic controls
- **Vault integration**: Secrets management via HashiCorp Vault Agent
- **Service mesh ready**: Istio sidecar injection annotations

### High Availability & Scaling
- **Horizontal Pod Autoscaler (HPA)**: Automatic scaling based on CPU/memory metrics
- **Pod Disruption Budgets (PDB)**: Ensures minimum replicas during maintenance
- **Anti-affinity rules**: Distributes pods across different nodes
- **Health checks**: Comprehensive liveness and readiness probes

## Directory Structure

```
gitops/
├── applications/           # ArgoCD Application manifests
│   ├── auth-service-app.yaml
│   ├── context-service-app.yaml
│   ├── text-summarization-app.yaml
│   └── mcp-platform-app.yaml  # App-of-Apps pattern
├── charts/                # Helm charts for new services
│   ├── auth-service/
│   │   ├── Chart.yaml
│   │   ├── values.yaml
│   │   └── templates/
│   └── context-service/
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
└── README.md
```

## Deployment Instructions

### Prerequisites
1. Kubernetes cluster with ArgoCD installed
2. HashiCorp Vault configured and accessible
3. Appropriate RBAC permissions for ArgoCD

### Initial Setup

1. **Deploy the App-of-Apps**:
   ```bash
   kubectl apply -f gitops/applications/mcp-platform-app.yaml
   ```

2. **Verify ArgoCD Applications**:
   ```bash
   kubectl get applications -n argocd
   ```

3. **Monitor Deployment Status**:
   ```bash
   argocd app list
   argocd app sync mcp-platform
   ```

### Vault Configuration

Each service requires specific Vault secrets:

#### Auth Service
```bash
# Database credentials (dynamic)
vault write database/config/auth-service \
    plugin_name=postgresql-database-plugin \
    connection_url="postgresql://{{username}}:{{password}}@postgres:5432/auth_db" \
    allowed_roles="auth-service"

# JWT secrets (static)
vault kv put secret/auth-service/jwt \
    secret="your-jwt-secret" \
    issuer="mcp-platform"
```

#### Context Service
```bash
# Database credentials (dynamic)
vault write database/config/context-service \
    plugin_name=postgresql-database-plugin \
    connection_url="postgresql://{{username}}:{{password}}@postgres:5432/context_db" \
    allowed_roles="context-service"

# Vector DB credentials (static)
vault kv put secret/context-service/vector-db \
    api_key="your-vector-db-api-key" \
    url="https://your-vector-db.com"
```

#### Text Summarization Service
```bash
# Database credentials (dynamic)
vault write database/config/text-summarization \
    plugin_name=postgresql-database-plugin \
    connection_url="postgresql://{{username}}:{{password}}@postgres:5432/summarization_db" \
    allowed_roles="readwrite"
```

### Service Configuration

#### Scaling Configuration
Each service is configured with HPA for automatic scaling:

- **Auth Service**: 2-10 replicas, 70% CPU / 80% Memory targets
- **Context Service**: 2-8 replicas, 70% CPU / 80% Memory targets  
- **Text Summarization**: 1-5 replicas, 70% CPU / 80% Memory targets

#### Network Security
All services include NetworkPolicy configurations:
- **Ingress**: Only from designated namespaces
- **Egress**: Restricted to Vault, databases, and DNS
- **Isolation**: Default deny with explicit allow rules

### Monitoring & Observability

Services are configured with:
- Prometheus metrics endpoints
- Structured JSON logging
- OpenTelemetry tracing
- Health check endpoints (`/health`, `/ready`, `/healthz`)

### Updating Services

1. **Image Updates**: Update image tags in ArgoCD applications
2. **Configuration Changes**: Modify values.yaml in respective charts
3. **GitOps Flow**: Changes sync automatically via ArgoCD

### Troubleshooting

#### Common Issues

1. **Vault Authentication Failures**:
   ```bash
   kubectl logs -n mcp-services deployment/auth-service -c vault-agent
   ```

2. **Pod Startup Issues**:
   ```bash
   kubectl describe pod -n mcp-services -l app.kubernetes.io/name=auth-service
   ```

3. **ArgoCD Sync Issues**:
   ```bash
   argocd app get auth-service --show-operation
   ```

#### Health Checks
```bash
# Check all services health
kubectl get pods -n mcp-services
kubectl get hpa -n mcp-services
kubectl get pdb -n mcp-services
```

## Security Considerations

1. **Secret Management**: All secrets managed via Vault with rotation
2. **RBAC**: Minimal service account permissions
3. **Network Isolation**: NetworkPolicies enforce micro-segmentation
4. **Image Security**: Use specific image tags, not `latest`
5. **Runtime Security**: Read-only filesystems and non-root execution

## Compliance & Governance

- **Change Management**: All changes tracked via Git commits
- **Audit Trail**: ArgoCD provides deployment history and rollback
- **Policy Enforcement**: OPA Gatekeeper policies (if configured)
- **Resource Quotas**: Namespace-level resource limits

For more information, refer to the individual service documentation and ArgoCD operational guides.
