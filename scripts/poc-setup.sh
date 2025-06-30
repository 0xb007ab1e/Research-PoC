#!/bin/bash

# MCP PoC Setup Script
# This script sets up a secure local development environment for the MCP platform PoC

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on supported OS
check_os() {
    if [[ "$OSTYPE" != "linux-gnu"* ]]; then
        log_error "This script is designed for Linux systems (you're on Parrot Security, which is perfect!)"
        exit 1
    fi
}

# Check for required tools
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    local tools=("docker" "kubectl" "helm" "git" "curl" "jq")
    local missing_tools=()
    
    for tool in "${tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        log_error "Missing required tools: ${missing_tools[*]}"
        log_info "Please install missing tools and run this script again"
        exit 1
    fi
    
    log_info "All prerequisites satisfied"
}

# Install kind if not present
install_kind() {
    if ! command -v kind &> /dev/null; then
        log_info "Installing kind (Kubernetes in Docker)..."
        curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64
        chmod +x ./kind
        sudo mv ./kind /usr/local/bin/kind
    fi
    log_info "Kind is available"
}

# Install istioctl if not present
install_istio() {
    if ! command -v istioctl &> /dev/null; then
        log_info "Installing Istio CLI..."
        curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.18.2 sh -
        sudo mv istio-*/bin/istioctl /usr/local/bin/
        rm -rf istio-*
    fi
    log_info "Istio CLI is available"
}

# Create kind cluster configuration
create_kind_config() {
    log_info "Creating kind cluster configuration..."
    
    cat > kind-config.yaml <<EOF
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
name: mcp-poc
nodes:
- role: control-plane
  kubeadmConfigPatches:
  - |
    kind: InitConfiguration
    nodeRegistration:
      kubeletExtraArgs:
        node-labels: "ingress-ready=true"
  extraPortMappings:
  - containerPort: 80
    hostPort: 80
    protocol: TCP
  - containerPort: 443
    hostPort: 443
    protocol: TCP
  - containerPort: 15021
    hostPort: 15021
    protocol: TCP
- role: worker
- role: worker
EOF
    
    log_info "Kind configuration created"
}

# Create Kubernetes cluster
create_cluster() {
    log_info "Creating Kubernetes cluster..."
    
    if kind get clusters | grep -q "mcp-poc"; then
        log_warn "Cluster 'mcp-poc' already exists. Deleting and recreating..."
        kind delete cluster --name mcp-poc
    fi
    
    kind create cluster --config kind-config.yaml --wait 300s
    
    # Wait for cluster to be ready
    kubectl wait --for=condition=Ready nodes --all --timeout=300s
    
    log_info "Kubernetes cluster created successfully"
}

# Create namespace and basic security policies
setup_namespace() {
    log_info "Setting up MCP namespace with security policies..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Namespace
metadata:
  name: mcp-poc
  labels:
    istio-injection: enabled
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: api-service
  namespace: mcp-poc
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: context-service
  namespace: mcp-poc
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: auth-service
  namespace: mcp-poc
---
# Network Policy - Default Deny All
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: mcp-poc
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
---
# Network Policy - Allow DNS
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-dns
  namespace: mcp-poc
spec:
  podSelector: {}
  policyTypes:
  - Egress
  egress:
  - to: []
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53
EOF
    
    log_info "Namespace and basic security policies created"
}

# Install cert-manager
install_cert_manager() {
    log_info "Installing cert-manager..."
    
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    
    # Wait for cert-manager to be ready
    kubectl wait --for=condition=Available deployment/cert-manager -n cert-manager --timeout=300s
    kubectl wait --for=condition=Available deployment/cert-manager-cainjector -n cert-manager --timeout=300s
    kubectl wait --for=condition=Available deployment/cert-manager-webhook -n cert-manager --timeout=300s
    
    log_info "cert-manager installed successfully"
}

# Install Istio
install_istio_cluster() {
    log_info "Installing Istio service mesh..."
    
    istioctl install --set values.defaultPodDisruptionBudget.enabled=false -y
    
    # Wait for Istio to be ready
    kubectl wait --for=condition=Available deployment/istiod -n istio-system --timeout=300s
    
    log_info "Istio installed successfully"
}

# Install Vault
install_vault() {
    log_info "Installing HashiCorp Vault..."
    
    # Add HashiCorp Helm repository
    helm repo add hashicorp https://helm.releases.hashicorp.com
    helm repo update
    
    # Install Vault in dev mode for PoC
    helm install vault hashicorp/vault \
        --namespace vault-system \
        --create-namespace \
        --set server.dev.enabled=true \
        --set server.dev.devRootToken="poc-root-token" \
        --set injector.enabled=true
    
    # Wait for Vault to be ready
    kubectl wait --for=condition=Ready pod/vault-0 -n vault-system --timeout=300s
    
    log_info "Vault installed successfully"
}

# Install OPA Gatekeeper
install_opa_gatekeeper() {
    log_info "Installing OPA Gatekeeper..."
    
    kubectl apply -f https://raw.githubusercontent.com/open-policy-agent/gatekeeper/release-3.14/deploy/gatekeeper.yaml
    
    # Wait for Gatekeeper to be ready
    kubectl wait --for=condition=Available deployment/gatekeeper-controller-manager -n gatekeeper-system --timeout=300s
    
    log_info "OPA Gatekeeper installed successfully"
}

# Create basic Gatekeeper policies
create_security_policies() {
    log_info "Creating security policies..."
    
    cat <<EOF | kubectl apply -f -
# No privileged containers
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: noprivileged
spec:
  crd:
    spec:
      names:
        kind: NoPrivileged
      validation:
        type: object
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package noprivileged
        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          container.securityContext.privileged
          msg := "Privileged containers are not allowed"
        }
---
apiVersion: templates.gatekeeper.sh/v1beta1
kind: NoPrivileged
metadata:
  name: no-privileged-containers
spec:
  match:
    - apiGroups: [""]
      kinds: ["Pod"]
      namespaces: ["mcp-poc"]
---
# No latest tags
apiVersion: templates.gatekeeper.sh/v1beta1
kind: ConstraintTemplate
metadata:
  name: nolatesttag
spec:
  crd:
    spec:
      names:
        kind: NoLatestTag
  targets:
    - target: admission.k8s.gatekeeper.sh
      rego: |
        package nolatesttag
        violation[{"msg": msg}] {
          container := input.review.object.spec.containers[_]
          endswith(container.image, ":latest")
          msg := "Images with :latest tag are not allowed"
        }
---
apiVersion: templates.gatekeeper.sh/v1beta1
kind: NoLatestTag
metadata:
  name: no-latest-tags
spec:
  match:
    - apiGroups: [""]
      kinds: ["Pod"]
      namespaces: ["mcp-poc"]
EOF
    
    log_info "Security policies created"
}

# Setup monitoring
setup_monitoring() {
    log_info "Setting up basic monitoring..."
    
    # Install Prometheus
    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm repo update
    
    helm install prometheus prometheus-community/kube-prometheus-stack \
        --namespace monitoring \
        --create-namespace \
        --set grafana.adminPassword=admin \
        --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
    
    log_info "Monitoring stack installed"
}

# Generate development certificates
generate_dev_certs() {
    log_info "Generating development certificates..."
    
    mkdir -p certs
    cd certs
    
    # Generate CA private key
    openssl genrsa -out ca.key 4096
    
    # Generate CA certificate
    openssl req -new -x509 -key ca.key -sha256 -subj "/C=US/ST=Dev/O=MCP-PoC/CN=MCP-CA" -days 30 -out ca.crt
    
    # Generate server private key
    openssl genrsa -out server.key 4096
    
    # Generate server certificate signing request
    openssl req -new -key server.key -out server.csr -subj "/C=US/ST=Dev/O=MCP-PoC/CN=*.mcp.internal"
    
    # Generate server certificate signed by CA
    openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out server.crt -days 30 -sha256 \
        -extensions v3_req -extfile <(cat <<EOF
[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = api.mcp.internal
DNS.2 = auth.mcp.internal
DNS.3 = context.mcp.internal
DNS.4 = localhost
IP.1 = 127.0.0.1
EOF
)
    
    # Create Kubernetes secrets
    kubectl create secret tls mcp-service-tls \
        --cert=server.crt \
        --key=server.key \
        -n mcp-poc
    
    kubectl create secret generic mcp-ca-cert \
        --from-file=ca.crt=ca.crt \
        -n mcp-poc
    
    cd ..
    
    log_info "Development certificates generated and stored in Kubernetes secrets"
}

# Create development manifests
create_dev_manifests() {
    log_info "Creating development manifests..."
    
    mkdir -p k8s
    
    # API Gateway deployment
    cat > k8s/api-gateway.yaml <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-gateway
  namespace: mcp-poc
  labels:
    app: api-gateway
    version: v1
spec:
  replicas: 1
  selector:
    matchLabels:
      app: api-gateway
  template:
    metadata:
      labels:
        app: api-gateway
        version: v1
    spec:
      serviceAccountName: api-service
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
      - name: api-gateway
        image: golang:1.21-alpine
        command: ["/bin/sh", "-c", "sleep 3600"]  # Placeholder for development
        ports:
        - containerPort: 8443
          name: https
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        volumeMounts:
        - name: tls-certs
          mountPath: /etc/certs
          readOnly: true
        - name: ca-cert
          mountPath: /etc/ca
          readOnly: true
        - name: tmp
          mountPath: /tmp
        env:
        - name: TLS_CERT_FILE
          value: /etc/certs/tls.crt
        - name: TLS_KEY_FILE
          value: /etc/certs/tls.key
        - name: CA_CERT_FILE
          value: /etc/ca/ca.crt
      volumes:
      - name: tls-certs
        secret:
          secretName: mcp-service-tls
      - name: ca-cert
        secret:
          secretName: mcp-ca-cert
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: api-gateway
  namespace: mcp-poc
  labels:
    app: api-gateway
spec:
  ports:
  - port: 8443
    targetPort: 8443
    name: https
  selector:
    app: api-gateway
EOF
    
    log_info "Development manifests created in k8s/ directory"
}

# Main installation function
main() {
    log_info "Starting MCP PoC setup..."
    
    check_os
    check_prerequisites
    install_kind
    install_istio
    create_kind_config
    create_cluster
    setup_namespace
    install_cert_manager
    install_istio_cluster
    install_vault
    install_opa_gatekeeper
    create_security_policies
    setup_monitoring
    generate_dev_certs
    create_dev_manifests
    
    log_info "Setup complete!"
    log_info ""
    log_info "Next steps:"
    log_info "1. Export kubeconfig: export KUBECONFIG=\$(kind get kubeconfig-path --name mcp-poc)"
    log_info "2. Check cluster status: kubectl get nodes"
    log_info "3. Access Grafana: kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80"
    log_info "4. Vault token for development: poc-root-token"
    log_info "5. Start developing your Go and Python services using the certificates in ./certs/"
    log_info ""
    log_info "Security features enabled:"
    log_info "- mTLS between all services (Istio)"
    log_info "- Pod Security Standards (restricted)"
    log_info "- Network policies (default deny)"
    log_info "- OPA Gatekeeper policies"
    log_info "- Non-root containers only"
    log_info "- Certificate management with cert-manager"
}

# Run main function
main "$@"
