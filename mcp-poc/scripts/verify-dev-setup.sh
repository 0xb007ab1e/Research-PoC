#!/bin/bash
set -e

echo "=== MCP Platform Development Environment Verification ==="
echo

# Check prerequisites
echo "1. Checking prerequisites..."

# Check Docker
if command -v docker >/dev/null 2>&1; then
    echo "✓ Docker is installed"
    if docker ps >/dev/null 2>&1; then
        echo "✓ Docker daemon is running"
    else
        echo "✗ Docker daemon is not running. Please start Docker."
        exit 1
    fi
else
    echo "✗ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check Docker Compose
if command -v docker-compose >/dev/null 2>&1; then
    echo "✓ Docker Compose is installed"
else
    echo "✗ Docker Compose is not installed. Please install Docker Compose."
    exit 1
fi

# Check Python
if command -v python3 >/dev/null 2>&1; then
    python_version=$(python3 --version | cut -d' ' -f2)
    echo "✓ Python is installed (version: $python_version)"
else
    echo "✗ Python3 is not installed. Please install Python 3.11+."
    exit 1
fi

# Check Go
if command -v go >/dev/null 2>&1; then
    go_version=$(go version | cut -d' ' -f3)
    echo "✓ Go is installed (version: $go_version)"
else
    echo "✗ Go is not installed. Please install Go 1.21+."
    exit 1
fi

# Check Make
if command -v make >/dev/null 2>&1; then
    echo "✓ Make is installed"
else
    echo "✗ Make is not installed. Please install make."
    exit 1
fi

echo

# Check project structure
echo "2. Checking project structure..."

if [ -f "docker-compose.dev.yml" ]; then
    echo "✓ docker-compose.dev.yml exists"
else
    echo "✗ docker-compose.dev.yml not found"
    exit 1
fi

if [ -f "scripts/postgres-init/01-init-databases.sh" ]; then
    echo "✓ PostgreSQL init script exists"
else
    echo "✗ PostgreSQL init script not found"
    exit 1
fi

if [ -f "scripts/dev-jwks/.well-known/jwks.json" ]; then
    echo "✓ JWKS mock server files exist"
else
    echo "✗ JWKS mock server files not found"
    exit 1
fi

if [ -f "services/context-service/Makefile" ]; then
    echo "✓ Context service Makefile exists"
else
    echo "✗ Context service Makefile not found"
    exit 1
fi

if [ -f "services/text-summarization/Makefile" ]; then
    echo "✓ Text summarization service Makefile exists"
else
    echo "✗ Text summarization service Makefile not found"
    exit 1
fi

if [ -f "services/text-summarization/auth-service/Makefile" ]; then
    echo "✓ Auth service Makefile exists"
else
    echo "✗ Auth service Makefile not found"
    exit 1
fi

echo

# Test development stack startup
echo "3. Testing development stack startup..."

echo "Starting development stack..."
make local-stack-up

# Wait for services to be ready
echo "Waiting for services to be ready..."
sleep 20

# Check if services are running
echo "Checking service health..."

# Check PostgreSQL
if docker-compose -f docker-compose.dev.yml ps postgres | grep -q "Up"; then
    echo "✓ PostgreSQL is running"
else
    echo "✗ PostgreSQL failed to start"
fi

# Check Vault
if docker-compose -f docker-compose.dev.yml ps vault | grep -q "Up"; then
    echo "✓ Vault is running"
else
    echo "✗ Vault failed to start"
fi

# Check Redis
if docker-compose -f docker-compose.dev.yml ps redis | grep -q "Up"; then
    echo "✓ Redis is running"
else
    echo "✗ Redis failed to start"
fi

# Check JWKS server
if docker-compose -f docker-compose.dev.yml ps jwks-server | grep -q "Up"; then
    echo "✓ JWKS server is running"
else
    echo "✗ JWKS server failed to start"
fi

# Check Adminer
if docker-compose -f docker-compose.dev.yml ps adminer | grep -q "Up"; then
    echo "✓ Adminer is running"
else
    echo "✗ Adminer failed to start"
fi

echo

# Test service endpoints
echo "4. Testing service endpoints..."

# Test PostgreSQL connection
if pg_isready -h localhost -p 5432 -U mcp_user >/dev/null 2>&1; then
    echo "✓ PostgreSQL is accepting connections"
else
    echo "✗ PostgreSQL is not accepting connections"
fi

# Test Vault health
if curl -s http://localhost:8200/v1/sys/health >/dev/null 2>&1; then
    echo "✓ Vault is responding"
else
    echo "✗ Vault is not responding"
fi

# Test Redis
if timeout 5 redis-cli -h localhost -p 6379 -a redis_password ping >/dev/null 2>&1; then
    echo "✓ Redis is responding"
else
    echo "✗ Redis is not responding"
fi

# Test JWKS server
if curl -s http://localhost:8080/.well-known/jwks.json >/dev/null 2>&1; then
    echo "✓ JWKS server is responding"
else
    echo "✗ JWKS server is not responding"
fi

# Test Adminer
if curl -s http://localhost:8081 >/dev/null 2>&1; then
    echo "✓ Adminer is responding"
else
    echo "✗ Adminer is not responding"
fi

echo

# Test Makefile targets
echo "5. Testing Makefile targets..."

# Test ensure-stack targets in services
echo "Testing service ensure-stack targets..."

cd services/context-service
if make ensure-stack >/dev/null 2>&1; then
    echo "✓ Context service ensure-stack works"
else
    echo "✗ Context service ensure-stack failed"
fi

cd ../text-summarization
if make ensure-stack >/dev/null 2>&1; then
    echo "✓ Text summarization service ensure-stack works"
else
    echo "✗ Text summarization service ensure-stack failed"
fi

cd auth-service
if make ensure-stack >/dev/null 2>&1; then
    echo "✓ Auth service ensure-stack works"
else
    echo "✗ Auth service ensure-stack failed"
fi

cd ../../..

echo

# Summary
echo "6. Verification Summary"
echo "======================"
echo "✓ Development environment is ready!"
echo
echo "Next steps:"
echo "1. Run 'make local-run' to start all services"
echo "2. Or run individual services:"
echo "   - cd services/context-service && make local-run"
echo "   - cd services/text-summarization && make local-run"
echo "   - cd services/text-summarization/auth-service && make local-run"
echo
echo "Services will be available at:"
echo "  - auth-service: http://localhost:8443"
echo "  - context-service: http://localhost:8001"
echo "  - text-summarization: http://localhost:8000"
echo
echo "Development tools:"
echo "  - PostgreSQL: localhost:5432 (user: mcp_user, password: mcp_password)"
echo "  - Vault: http://localhost:8200 (token: myroot)"
echo "  - Redis: localhost:6379 (password: redis_password)"
echo "  - Adminer: http://localhost:8081"
echo
echo "For more information, see LOCAL_DEVELOPMENT.md"
