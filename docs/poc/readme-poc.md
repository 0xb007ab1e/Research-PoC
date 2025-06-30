# MCP PoC Quick Start Guide

## Overview

This guide will help you set up and run a Proof of Concept (PoC) for the Multi-tenant Context Platform (MCP) with a focus on security-first architecture, least privilege principles, and certificate-based authentication.

## Prerequisites

Ensure you have the following tools installed on your Parrot Security system:

```bash
# Check if tools are installed
docker --version
kubectl version --client
helm version
git --version
curl --version
jq --version
```

If any tools are missing, install them:

```bash
# Install missing tools on Parrot Security/Debian
sudo apt update
sudo apt install docker.io kubectl helm git curl jq

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

## Quick Setup

1. **Run the automated setup script:**
   ```bash
   ./scripts/poc-setup.sh
   ```

   This script will:
   - Install kind and istioctl if needed
   - Create a secure Kubernetes cluster
   - Set up Istio service mesh with mTLS
   - Install HashiCorp Vault for secrets management
   - Configure OPA Gatekeeper for policy enforcement
   - Generate development certificates
   - Set up monitoring with Prometheus and Grafana

2. **Verify the setup:**
   ```bash
   # Check cluster status
   kubectl get nodes
   
   # Check all pods are running
   kubectl get pods --all-namespaces
   
   # Verify security policies
   kubectl get constraints
   ```

## Security Features Implemented

### 1. Zero Trust Networking
- **Istio Service Mesh**: All service-to-service communication uses mTLS
- **Network Policies**: Default deny-all with explicit allow rules
- **Certificate Management**: Automated certificate rotation with 24-hour TTL

### 2. Least Privilege Access
- **Pod Security Standards**: Restricted security context for all pods
- **RBAC**: Minimal permissions for service accounts
- **Non-root Containers**: All containers run as non-root users
- **Read-only Filesystems**: Containers use read-only root filesystems

### 3. Policy Enforcement
- **OPA Gatekeeper**: Prevents privileged containers and latest tags
- **Admission Controllers**: Security policies enforced at admission time
- **Audit Logging**: All policy violations are logged

### 4. Secrets Management
- **HashiCorp Vault**: Dynamic secrets with short TTL
- **No Hardcoded Secrets**: All secrets injected at runtime
- **Certificate Rotation**: Automated certificate lifecycle management

## Development Workflows

### 1. User Authentication & Authorization Workflow

This workflow demonstrates OAuth2.1 PKCE with certificate-based service authentication:

```bash
# Create a test client certificate
cd certs/
openssl genrsa -out client.key 4096
openssl req -new -key client.key -out client.csr -subj "/C=US/ST=Dev/O=MCP-Client/CN=test-client"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out client.crt -days 30 -sha256

# Test mTLS connection
curl -k --cert client.crt --key client.key --cacert ca.crt \
  https://localhost:8443/health
```

### 2. Context Query & Response Workflow

This workflow demonstrates multi-tenant data isolation:

```bash
# Deploy a test context service
kubectl apply -f k8s/api-gateway.yaml

# Test tenant isolation
kubectl exec -it deployment/api-gateway -n mcp-poc -- /bin/sh
```

## Monitoring and Observability

### Access Grafana Dashboard
```bash
# Port forward Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80

# Access at http://localhost:3000
# Username: admin
# Password: admin
```

### Access Prometheus
```bash
# Port forward Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Access at http://localhost:9090
```

### View Security Metrics
Key metrics to monitor:
- `gatekeeper_violations_total` - Policy violations
- `istio_request_total` - Service mesh traffic
- `cert_manager_certificate_expiration_timestamp_seconds` - Certificate expiry

## Vault Integration

### Access Vault UI
```bash
# Port forward Vault
kubectl port-forward -n vault-system svc/vault 8200:8200

# Access at http://localhost:8200
# Token: poc-root-token
```

### Configure Dynamic Database Secrets
```bash
# Exec into Vault pod
kubectl exec -it vault-0 -n vault-system -- /bin/sh

# Enable database secrets engine
vault auth -method=token token=poc-root-token
vault secrets enable database

# Configure PostgreSQL (when you add it to your PoC)
vault write database/config/postgresql \
    plugin_name=postgresql-database-plugin \
    connection_url="postgresql://postgres:password@postgres:5432/mydb?sslmode=require" \
    allowed_roles="readonly,readwrite"
```

## Security Testing

### Test Network Policies
```bash
# Try to access denied services (should fail)
kubectl run test-pod --image=busybox --rm -it --restart=Never -n mcp-poc -- \
  wget -qO- http://prometheus-grafana.monitoring:80
```

### Test OPA Policies
```bash
# Try to create privileged pod (should be denied)
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: privileged-pod
  namespace: mcp-poc
spec:
  containers:
  - name: test
    image: busybox:latest
    securityContext:
      privileged: true
EOF
```

### Vulnerability Scanning
```bash
# Scan your images for vulnerabilities
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image golang:1.21-alpine
```

## Development Best Practices

### 1. Certificate Management
- Use the generated certificates in `./certs/` for local development
- Never commit certificates to version control
- Certificates automatically rotate every 24 hours in production

### 2. Secret Handling
- Always retrieve secrets from Vault
- Use environment variables for configuration
- Never hardcode secrets in source code

### 3. Security Testing
- Run `trivy` scans on all container images
- Test network policies with different scenarios
- Validate RBAC permissions regularly

### 4. Monitoring
- Set up alerts for certificate expiry
- Monitor policy violations
- Track service mesh metrics

## Next Steps

1. **Develop Go API Gateway:**
   - Implement OAuth2.1 PKCE flow
   - Add tenant routing logic
   - Integrate with Vault for secrets

2. **Develop Python Context Service:**
   - Implement FastAPI with mTLS
   - Add ML model integration
   - Implement tenant data isolation

3. **Add Database Layer:**
   - Deploy PostgreSQL with pgvector
   - Configure schema-based tenant isolation
   - Integrate with Vault for dynamic credentials

4. **Enhance Security:**
   - Add more OPA policies
   - Implement audit logging
   - Set up SIEM integration

## Troubleshooting

### Common Issues

1. **Pods not starting:**
   ```bash
   kubectl describe pod <pod-name> -n mcp-poc
   kubectl logs <pod-name> -n mcp-poc
   ```

2. **Certificate issues:**
   ```bash
   kubectl get certificates -n mcp-poc
   kubectl describe certificate mcp-service-cert -n mcp-poc
   ```

3. **Network connectivity:**
   ```bash
   kubectl exec -it <pod-name> -n mcp-poc -- nslookup kubernetes.default
   ```

4. **Policy violations:**
   ```bash
   kubectl get events -n mcp-poc --sort-by=.metadata.creationTimestamp
   ```

### Cleanup
```bash
# Delete the entire PoC environment
kind delete cluster --name mcp-poc
docker system prune -f
```

## Security Compliance Checklist

- [ ] All containers run as non-root
- [ ] No privileged containers allowed
- [ ] All communications use mTLS
- [ ] Secrets managed by Vault
- [ ] Network policies enforce isolation
- [ ] Pod Security Standards enforced
- [ ] Certificates rotate automatically
- [ ] Audit logging enabled
- [ ] Vulnerability scanning integrated
- [ ] RBAC follows least privilege

This PoC demonstrates enterprise-grade security practices while maintaining development agility. Use this foundation to build your full MCP platform implementation.
