# PostgreSQL with pgvector Helm Chart

This Helm chart deploys PostgreSQL with pgvector extension for the MCP PoC project.

## Features

- **pgvector Extension**: Enables vector similarity search capabilities
- **Namespace Isolation**: Deployed in `mcp-poc` namespace
- **Network Security**: NetworkPolicy restricts access to `context-service` and `auth-service` only
- **TLS Encryption**: Self-signed certificates via cert-manager for secure connections
- **High Availability**: Configurable with persistence and resource limits

## Prerequisites

- Kubernetes cluster with NetworkPolicy support
- Helm 3.x
- cert-manager installed in the cluster
- Bitnami PostgreSQL Helm chart repository

## Installation

1. Add the Bitnami Helm repository:
```bash
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
```

2. Install cert-manager (if not already installed):
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

3. Install the PostgreSQL chart:
```bash
helm install postgresql-mcp ./charts/postgresql -n mcp-poc --create-namespace
```

## Configuration

### Database Connection

- **Host**: `postgresql-mcp.mcp-poc.svc.cluster.local`
- **Port**: `5432`
- **Database**: `mcp_poc`
- **Username**: `mcp_user`
- **Password**: Set in values.yaml (change default)

### TLS Connection

The database is configured with TLS encryption. Client applications should:
- Use SSL mode `require` or `verify-ca`
- Trust the self-signed certificate from the `postgresql-tls-certs` secret

### pgvector Usage

The pgvector extension is automatically enabled. You can use vector operations:

```sql
-- Create table with vector column
CREATE TABLE embeddings (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(1536)
);

-- Insert vector data
INSERT INTO embeddings (content, embedding) VALUES 
    ('sample text', '[0.1, 0.2, 0.3, ...]');

-- Similarity search
SELECT content FROM embeddings 
ORDER BY embedding <-> '[0.1, 0.2, 0.3, ...]' 
LIMIT 10;
```

## Security

### Network Policy

The NetworkPolicy restricts database access to:
- Pods labeled with `app.kubernetes.io/name: context-service`
- Pods labeled with `app.kubernetes.io/name: auth-service`
- Pods with service accounts `context-service` or `auth-service`

### Service Accounts

Ensure your applications run with the appropriate service accounts:
- `context-service` service account for context service pods
- `auth-service` service account for auth service pods

## Monitoring

Metrics are enabled by default. You can access PostgreSQL metrics through the metrics service.

## Troubleshooting

### Check PostgreSQL pods:
```bash
kubectl get pods -n mcp-poc -l app.kubernetes.io/name=postgresql
```

### Check TLS certificates:
```bash
kubectl get certificates -n mcp-poc
kubectl describe certificate postgresql-tls-cert -n mcp-poc
```

### Check NetworkPolicy:
```bash
kubectl get networkpolicy -n mcp-poc
kubectl describe networkpolicy postgresql-network-policy -n mcp-poc
```

### Test database connection:
```bash
kubectl run -it --rm debug --image=postgres:15 --restart=Never -n mcp-poc -- psql -h postgresql-mcp.mcp-poc.svc.cluster.local -U mcp_user -d mcp_poc
```

## Customization

Modify `values.yaml` to customize:
- Resource limits and requests
- Storage size and class
- PostgreSQL configuration parameters
- Authentication credentials (use Kubernetes secrets in production)
- TLS certificate settings
