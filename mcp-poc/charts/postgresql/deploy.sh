#!/bin/bash

set -e

echo "Deploying PostgreSQL with pgvector for MCP PoC..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if helm is installed
if ! command -v helm &> /dev/null; then
    echo -e "${RED}Error: Helm is not installed${NC}"
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl is not installed${NC}"
    exit 1
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Adding Bitnami Helm repository...${NC}"
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

echo -e "${YELLOW}Step 2: Checking cert-manager installation...${NC}"
if ! kubectl get namespace cert-manager &> /dev/null; then
    echo -e "${YELLOW}Installing cert-manager...${NC}"
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
    
    echo -e "${YELLOW}Waiting for cert-manager to be ready...${NC}"
    kubectl wait --for=condition=ready pod -l app=cert-manager -n cert-manager --timeout=300s
    kubectl wait --for=condition=ready pod -l app=cainjector -n cert-manager --timeout=300s
    kubectl wait --for=condition=ready pod -l app=webhook -n cert-manager --timeout=300s
else
    echo -e "${GREEN}cert-manager is already installed${NC}"
fi

echo -e "${YELLOW}Step 3: Creating namespace mcp-poc...${NC}"
kubectl create namespace mcp-poc --dry-run=client -o yaml | kubectl apply -f -

echo -e "${YELLOW}Step 4: Updating Helm dependencies...${NC}"
helm dependency update ./charts/postgresql

echo -e "${YELLOW}Step 5: Installing PostgreSQL with pgvector...${NC}"
helm upgrade --install postgresql-mcp ./charts/postgresql \
    --namespace mcp-poc \
    --create-namespace \
    --wait \
    --timeout=600s

echo -e "${YELLOW}Step 6: Waiting for PostgreSQL to be ready...${NC}"
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql -n mcp-poc --timeout=300s

echo -e "${YELLOW}Step 7: Verifying pgvector extension...${NC}"
# Wait a bit more for the database to fully initialize
sleep 30

kubectl run --rm -i --tty pgvector-test \
  --image=postgres:15 \
  --restart=Never \
  --namespace=mcp-poc \
  --command -- psql \
  "postgresql://mcp_user:changeme@postgresql-mcp.mcp-poc.svc.cluster.local:5432/mcp_poc?sslmode=require" \
  -c "SELECT * FROM pg_extension WHERE extname='vector';" || true

echo -e "${GREEN}Deployment completed successfully!${NC}"
echo ""
echo -e "${YELLOW}Connection Details:${NC}"
echo "Host: postgresql-mcp.mcp-poc.svc.cluster.local"
echo "Port: 5432"
echo "Database: mcp_poc"
echo "Username: mcp_user"
echo "Password: changeme (change this in production!)"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Update your application configuration to use the above connection details"
echo "2. Ensure your application pods have the correct labels for NetworkPolicy"
echo "3. Configure your application to use TLS when connecting to the database"
echo "4. Change the default passwords in production!"
