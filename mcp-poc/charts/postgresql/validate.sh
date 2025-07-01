#!/bin/bash

set -e

echo "Validating PostgreSQL with pgvector deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Checking namespace...${NC}"
if kubectl get namespace mcp-poc &> /dev/null; then
    echo -e "${GREEN}✓ Namespace mcp-poc exists${NC}"
else
    echo -e "${RED}✗ Namespace mcp-poc not found${NC}"
    exit 1
fi

echo -e "${YELLOW}Checking PostgreSQL pods...${NC}"
if kubectl get pods -n mcp-poc -l app.kubernetes.io/name=postgresql | grep -q Running; then
    echo -e "${GREEN}✓ PostgreSQL pods are running${NC}"
else
    echo -e "${RED}✗ PostgreSQL pods are not running${NC}"
    kubectl get pods -n mcp-poc -l app.kubernetes.io/name=postgresql
fi

echo -e "${YELLOW}Checking PostgreSQL service...${NC}"
if kubectl get svc -n mcp-poc postgresql-mcp &> /dev/null; then
    echo -e "${GREEN}✓ PostgreSQL service exists${NC}"
    kubectl get svc -n mcp-poc postgresql-mcp
else
    echo -e "${RED}✗ PostgreSQL service not found${NC}"
fi

echo -e "${YELLOW}Checking TLS certificates...${NC}"
if kubectl get certificate -n mcp-poc postgresql-tls-cert &> /dev/null; then
    CERT_STATUS=$(kubectl get certificate -n mcp-poc postgresql-tls-cert -o jsonpath='{.status.conditions[0].status}')
    if [ "$CERT_STATUS" = "True" ]; then
        echo -e "${GREEN}✓ TLS certificate is ready${NC}"
    else
        echo -e "${YELLOW}⚠ TLS certificate is not ready yet${NC}"
        kubectl describe certificate -n mcp-poc postgresql-tls-cert
    fi
else
    echo -e "${RED}✗ TLS certificate not found${NC}"
fi

echo -e "${YELLOW}Checking NetworkPolicy...${NC}"
if kubectl get networkpolicy -n mcp-poc postgresql-network-policy &> /dev/null; then
    echo -e "${GREEN}✓ NetworkPolicy exists${NC}"
else
    echo -e "${RED}✗ NetworkPolicy not found${NC}"
fi

echo -e "${YELLOW}Testing database connection...${NC}"
CONNECTION_TEST=$(kubectl run --rm -i --quiet --restart=Never test-connection \
  --image=postgres:15 \
  --namespace=mcp-poc \
  --command -- timeout 10 psql \
  "postgresql://mcp_user:changeme@postgresql-mcp.mcp-poc.svc.cluster.local:5432/mcp_poc?sslmode=require" \
  -c "SELECT 1;" 2>&1 || echo "Connection failed")

if echo "$CONNECTION_TEST" | grep -q "1"; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    echo "$CONNECTION_TEST"
fi

echo -e "${YELLOW}Testing pgvector extension...${NC}"
PGVECTOR_TEST=$(kubectl run --rm -i --quiet --restart=Never test-pgvector \
  --image=postgres:15 \
  --namespace=mcp-poc \
  --command -- timeout 10 psql \
  "postgresql://mcp_user:changeme@postgresql-mcp.mcp-poc.svc.cluster.local:5432/mcp_poc?sslmode=require" \
  -c "SELECT extname FROM pg_extension WHERE extname='vector';" 2>&1 || echo "pgvector test failed")

if echo "$PGVECTOR_TEST" | grep -q "vector"; then
    echo -e "${GREEN}✓ pgvector extension is installed and working${NC}"
else
    echo -e "${RED}✗ pgvector extension test failed${NC}"
    echo "$PGVECTOR_TEST"
fi

echo ""
echo -e "${GREEN}Validation completed!${NC}"
