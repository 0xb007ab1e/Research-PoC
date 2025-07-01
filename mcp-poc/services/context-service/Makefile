# MCP Context Service Makefile
# Provides convenient commands for development, testing, and security scanning

.PHONY: help install test security-scan lint format clean run local-run run-prod docker-build

# Default target
help:
	@echo "Available commands:"
	@echo "  install        - Install dependencies"
	@echo "  test          - Run unit tests"
	@echo "  security-scan - Run basic security scans (Bandit + Safety)"
	@echo "  lint          - Run code linting (flake8, mypy)"
	@echo "  format        - Format code (black, isort)"
	@echo "  clean         - Clean up temporary files"
	@echo "  run           - Run service in development mode"
	@echo "  local-run     - Run service locally for development"
	@echo "  run-prod      - Run service in production mode"
	@echo "  docker-build  - Build Docker image"

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

# Run service in development mode
run:
	@echo "Starting context service in development mode..."
	python main.py

# Ensure compose stack is up
ensure-stack:
	@echo "Checking if development stack is running..."
	@docker-compose -f ../../docker-compose.dev.yml ps | grep -q "Up" || { \
		echo "Starting development stack..."; \
		docker-compose -f ../../docker-compose.dev.yml up -d; \
		echo "Waiting for services to be ready..."; \
		sleep 15; \
	}

# Run service locally for development
local-run: install ensure-stack
	@echo "Setting up environment variables..."
	@export DB_HOST=localhost && \
	export DB_PORT=5432 && \
	export DB_NAME=context_service && \
	export DB_USER=context_service_user && \
	export DB_PASSWORD=context_service_password && \
	export VAULT_ADDR=http://localhost:8200 && \
	export VAULT_TOKEN=myroot && \
	export AUTH_SERVICE_URL=http://localhost:8080 && \
	export REDIS_URL=redis://:redis_password@localhost:6379/0 && \
	export ENVIRONMENT=development && \
	export DEBUG=true && \
	export ENABLE_TLS=false && \
	export REQUIRE_TENANT_ID=false && \
	echo "Bootstrapping database..." && \
	python scripts/db-bootstrap.py --health-check || python scripts/db-bootstrap.py && \
	echo "Starting context service with hot-reload..." && \
	uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Run service in production mode
run-prod:
	@echo "Starting context service in production mode..."
	ENVIRONMENT=production DEBUG=false uvicorn main:app --host 0.0.0.0 --port 8001

# Docker commands
docker-build:
	@echo "Building Docker image..."
	docker build -t context-service:latest .

# CI/CD pipeline simulation
ci: clean install lint security-scan test
	@echo "CI pipeline completed successfully!"

# All-in-one development setup
dev-setup: install
	@echo "Development environment setup complete!"
	@echo "You can now run 'make run' to start the service"
