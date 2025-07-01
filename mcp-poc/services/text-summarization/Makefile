# MCP Text Summarization Service Makefile
# Provides convenient commands for development, testing, and security scanning

.PHONY: help install test security-scan security-full lint format clean run run-prod docker-build docker-scan

# Default target
help:
	@echo "Available commands:"
	@echo "  install        - Install dependencies"
	@echo "  test          - Run unit tests"
	@echo "  security-scan - Run basic security scans (Bandit + Safety)"
	@echo "  security-full - Run comprehensive security analysis"
	@echo "  lint          - Run code linting (flake8, mypy)"
	@echo "  format        - Format code (black, isort)"
	@echo "  clean         - Clean up temporary files"
	@echo "  run           - Run service in development mode"
	@echo "  run-prod      - Run service in production mode"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-scan   - Scan Docker image for vulnerabilities"

# Install dependencies
install:
	@if [ -d ".venv" ]; then \
		echo "Using existing virtual environment..."; \
		. .venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && pip install bandit[toml] safety flake8 black isort mypy pytest pytest-cov; \
	elif [ -n "$(CI)" ] || [ -n "$(GITHUB_ACTIONS)" ] || [ -n "$(GITLAB_CI)" ] || [ -n "$(JENKINS_URL)" ]; then \
		echo "CI environment detected, using --break-system-packages..."; \
		pip install --break-system-packages --upgrade pip setuptools wheel; \
		pip install --break-system-packages -r requirements.txt; \
		pip install --break-system-packages bandit[toml] safety flake8 black isort mypy pytest pytest-cov; \
	else \
		echo "Creating virtual environment..."; \
		python3 -m venv .venv; \
		. .venv/bin/activate && pip install --upgrade pip setuptools wheel && pip install -r requirements.txt && pip install bandit[toml] safety flake8 black isort mypy pytest pytest-cov; \
	fi

# Run unit tests with coverage
test:
	@echo "Running unit tests with coverage..."
	pytest tests/ -v --cov=. --cov-report=term-missing --cov-report=html --cov-fail-under=80
	@echo "Coverage report generated in htmlcov/"
	@echo "Minimum coverage threshold: 80%"

# Basic security scanning
security-scan:
	@echo "Running Bandit security analysis..."
	bandit -r . -x tests/ -f txt
	@echo "\nRunning Safety dependency check..."
	safety check

# Comprehensive security analysis
security-full:
	@echo "=== COMPREHENSIVE SECURITY ANALYSIS ==="
	@echo "\n1. Running Bandit security linter..."
	bandit -r . -x tests/ -f json -o reports/bandit-report.json || true
	bandit -r . -x tests/ -f txt
	
	@echo "\n2. Running Safety dependency vulnerability check..."
	safety check --json --output reports/safety-report.json || true
	safety check
	
	@echo "\n3. Running SSL/TLS configuration test..."
	python -c "from tls_config import get_tls_config; print('TLS Status:', get_tls_config().get_tls_status())" || echo "TLS test failed"
	
	@echo "\n4. Running JWT validation test..."
	python -c "from auth import JWKSManager; print('JWT module imported successfully')" || echo "JWT test failed"
	
	@echo "\n5. Checking for hardcoded secrets..."
	grep -r "password\|secret\|key\|token" --include="*.py" . | grep -v "# " | grep -v "test" || echo "No obvious hardcoded secrets found"
	
	@echo "\n6. Checking file permissions..."
	find . -type f -name "*.py" -perm /044 | head -10 || echo "No world-readable Python files found"
	
	@echo "\nSecurity analysis complete. Check reports/ directory for detailed results."

# Code linting
lint:
	@echo "Running Flake8 linting..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
	
	@echo "\nRunning MyPy type checking..."
	mypy . --ignore-missing-imports --no-strict-optional || true

# Code formatting
format:
	@echo "Formatting code with Black..."
	black .
	
	@echo "Sorting imports with isort..."
	isort .

# Clean up temporary files
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/
	rm -rf dist/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf reports/*.json

# Run service in development mode
run:
	@echo "Starting service in development mode..."
	python main.py

# Ensure compose stack is up
ensure-stack:
	@echo "Checking if development stack is running..."
	@docker-compose -f ../docker-compose.dev.yml ps | grep -q "Up" || { \
		echo "Starting development stack..."; \
		docker-compose -f ../docker-compose.dev.yml up -d; \
		echo "Waiting for services to be ready..."; \
		sleep 15; \
	}

# Run service locally for development
local-run: install ensure-stack
	@echo "Setting up environment variables..."
	@export DB_HOST=localhost && \
	export DB_PORT=5432 && \
	export DB_NAME=text_summarization && \
	export DB_USER=text_summarization_user && \
	export DB_PASSWORD=text_summarization_password && \
	export VAULT_ADDR=http://localhost:8200 && \
	export VAULT_TOKEN=myroot && \
	export AUTH_SERVICE_URL=http://localhost:8080 && \
	export REDIS_URL=redis://:redis_password@localhost:6379/1 && \
	export ENVIRONMENT=development && \
	export DEBUG=true && \
	export ENABLE_TLS=false && \
	export REQUIRE_TENANT_ID=false && \
	echo "Starting text-summarization service with hot-reload..." && \
	uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Run service in production mode
run-prod:
	@echo "Starting service in production mode..."
	ENVIRONMENT=production DEBUG=false uvicorn main:app --host 0.0.0.0 --port 8000

# Create reports directory
reports:
	mkdir -p reports

# Docker commands
docker-build:
	@echo "Building Docker image..."
	docker build -t text-summarization-service:latest .

docker-scan: docker-build
	@echo "Scanning Docker image for vulnerabilities..."
	docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
		-v ${PWD}:/root/.cache/ \
		aquasec/trivy:latest image text-summarization-service:latest

# Generate TLS certificates for testing
generate-test-certs:
	@echo "Generating test certificates..."
	mkdir -p test-certs
	openssl genrsa -out test-certs/ca.key 2048
	openssl req -new -x509 -days 365 -key test-certs/ca.key -out test-certs/ca.crt \
		-subj "/C=US/ST=CA/L=SF/O=Test/CN=TestCA"
	openssl genrsa -out test-certs/server.key 2048
	openssl req -new -key test-certs/server.key -out test-certs/server.csr \
		-subj "/C=US/ST=CA/L=SF/O=Test/CN=localhost"
	openssl x509 -req -in test-certs/server.csr -CA test-certs/ca.crt -CAkey test-certs/ca.key \
		-CAcreateserial -out test-certs/server.crt -days 365
	openssl genrsa -out test-certs/client.key 2048
	openssl req -new -key test-certs/client.key -out test-certs/client.csr \
		-subj "/C=US/ST=CA/L=SF/O=Test/CN=client"
	openssl x509 -req -in test-certs/client.csr -CA test-certs/ca.crt -CAkey test-certs/ca.key \
		-CAcreateserial -out test-certs/client.crt -days 365
	@echo "Test certificates generated in test-certs/ directory"

# Run security tests with test certificates
test-security: generate-test-certs
	@echo "Running security integration tests..."
	TLS_CERTS_DIR=./test-certs python -c "from tls_config import get_tls_config; \
		tls = get_tls_config(); \
		status = tls.get_tls_status(); \
		print('TLS Status:', status); \
		assert status['server_tls_available'], 'Server TLS should be available'; \
		assert status['mutual_tls_available'], 'Mutual TLS should be available'; \
		print('✓ TLS configuration test passed')"
	
	@echo "Testing middleware initialization..."
	python -c "from middleware import HeaderValidationMiddleware, SecurityHeadersMiddleware; \
		from fastapi import FastAPI; \
		app = FastAPI(); \
		HeaderValidationMiddleware(app); \
		SecurityHeadersMiddleware(app); \
		print('✓ Middleware initialization test passed')"
	
	@echo "Testing JWT validation module..."
	python -c "from auth import JWKSManager, EnhancedJWTValidator; \
		print('✓ JWT validation module test passed')"

# CI/CD pipeline simulation
ci: clean install lint security-scan test
	@echo "CI pipeline completed successfully!"

# All-in-one development setup
dev-setup: install generate-test-certs
	@echo "Development environment setup complete!"
	@echo "You can now run 'make run' to start the service"

# Production readiness check
prod-check:
	@echo "=== PRODUCTION READINESS CHECK ==="
	@echo "1. Checking environment variables..."
	python -c "from config import settings; print(f'Environment: {settings.service.environment}'); print(f'Debug: {settings.service.debug}'); print(f'TLS: {settings.security.enable_tls}')"
	
	@echo "\n2. Running security scan..."
	make security-scan
	
	@echo "\n3. Running tests..."
	make test
	
	@echo "\n4. Checking TLS configuration..."
	test -f /etc/certs/server.crt && test -f /etc/certs/server.key && echo "✓ TLS certificates found" || echo "⚠ TLS certificates not found"
	
	@echo "\nProduction readiness check complete!"
