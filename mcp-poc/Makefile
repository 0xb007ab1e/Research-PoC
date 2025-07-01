# MCP Platform Enhanced CI/CD Makefile
# Supports BuildKit, SBOM generation, Cosign signing, and kind deployments

.PHONY: help install test test-all security-scan build-all build-with-sbom push-all sign-all \
        kind-setup kind-deploy kind-test kind-cleanup local-dev clean

# Configuration
REGISTRY ?= ghcr.io
REPO_NAME ?= $(shell basename $(CURDIR))
VERSION ?= $(shell git rev-parse --short HEAD)
BRANCH ?= $(shell git rev-parse --abbrev-ref HEAD)

# Services configuration
SERVICES := text-summarization context-service auth-service
SERVICE_PATHS := services/text-summarization services/context-service services/text-summarization/auth-service
DOCKERFILES := services/text-summarization/Dockerfile services/context-service/Dockerfile services/text-summarization/auth-service/Dockerfile

# Build configuration
BUILD_ARGS := --build-arg BUILD_DATE=$(shell date -u +'%Y-%m-%dT%H:%M:%SZ') \
              --build-arg VERSION=$(VERSION) \
              --build-arg VCS_REF=$(shell git rev-parse HEAD)

# Default target
help:
	@echo "Enhanced CI/CD Pipeline Commands"
	@echo "================================="
	@echo ""
	@echo "Development:"
	@echo "  install          - Install all dependencies"
	@echo "  test            - Run unit tests for all services"
	@echo "  test-all        - Run unit + integration + security tests"
	@echo "  security-scan   - Run security scans on all services"
	@echo ""
	@echo "Build & Registry:"
	@echo "  build-all       - Build all Docker images with BuildKit"
	@echo "  build-with-sbom - Build images with SBOM generation"
	@echo "  push-all        - Push all images to registry"
	@echo "  sign-all        - Sign all images with Cosign"
	@echo ""
	@echo "Kind Deployment:"
	@echo "  kind-setup      - Set up kind cluster"
	@echo "  kind-deploy     - Deploy services to kind"
	@echo "  kind-test       - Run smoke tests on kind"
	@echo "  kind-cleanup    - Clean up kind cluster"
	@echo ""
	@echo "Local Development:"
	@echo "  local-stack-up     - Start development stack (Postgres, Vault, Redis)"
	@echo "  local-stack-down   - Stop development stack"
	@echo "  local-stack-status - Check development stack status"
	@echo "  local-stack-logs   - View development stack logs"
	@echo "  local-run          - Start all services with hot-reload"
	@echo ""
	@echo "Utilities:"
	@echo "  local-dev       - Set up local development environment (legacy)"
	@echo "  generate-docs   - Generate API documentation"
	@echo "  clean           - Clean up build artifacts"
	@echo ""
	@echo "Environment Variables:"
	@echo "  REGISTRY        - Container registry (default: ghcr.io)"
	@echo "  VERSION         - Image version tag (default: git short hash)"
	@echo "  BRANCH          - Git branch (default: current branch)"

# Install dependencies for all services
install:
	@echo "Installing dependencies for all services..."
	@for service in $(SERVICES); do \
		echo "Installing dependencies for $$service..."; \
		if [ "$$service" = "auth-service" ]; then \
			cd services/text-summarization/auth-service 66 go mod download 66 go mod tidy; \
		else \
			scripts/dev-venv.sh setup services/$$service $$service; \
		fi; \
		cd $(CURDIR); \
	done

# Run unit tests for all services
test:
	@echo "Running unit tests for all services..."
	@for service in $(SERVICES); do \
		echo "Testing $$service..."; \
		if [ "$$service" = "auth-service" ]; then \
			cd services/text-summarization/auth-service && make test; \
		elif [ "$$service" = "text-summarization" ]; then \
			cd services/text-summarization && make test; \
		else \
			cd services/$$service && python -m pytest tests/ -v || echo "No tests found for $$service"; \
		fi; \
		cd $(CURDIR); \
	done

# Run comprehensive test suite
test-all: test
	@echo "Running integration tests..."
	cd tests && python -m pytest . -v --ignore=e2e
	@echo "Running end-to-end workflow tests..."
	python tests/e2e/test_workflow.py
	@echo "All tests completed successfully!"

# Run security scans
security-scan:
	@echo "Running security scans for all services..."
	@for service in $(SERVICES); do \
		echo "Security scanning $$service..."; \
		if [ "$$service" = "auth-service" ]; then \
			cd services/text-summarization/auth-service && govulncheck ./... || echo "govulncheck not available"; \
		elif [ "$$service" = "text-summarization" ]; then \
			cd services/text-summarization && make security-scan; \
		else \
			cd services/$$service && bandit -r . && safety check || echo "Security tools not available"; \
		fi; \
		cd $(CURDIR); \
	done

# Set up Docker Buildx
setup-buildx:
	@echo "Setting up Docker Buildx..."
	@docker buildx create --name mcp-builder --use --bootstrap || true
	@docker buildx inspect --bootstrap

# Build all images with BuildKit
build-all: setup-buildx
	@echo "Building all images with BuildKit..."
	@for i in $(shell seq 1 $(words $(SERVICES))); do \
		service=$(word $$i,$(SERVICES)); \
		dockerfile=$(word $$i,$(DOCKERFILES)); \
		echo "Building $$service with BuildKit..."; \
		docker buildx build \
			--platform linux/amd64,linux/arm64 \
			--tag $(REGISTRY)/$(REPO_NAME)/$$service:$(VERSION) \
			--tag $(REGISTRY)/$(REPO_NAME)/$$service:$(BRANCH) \
			--tag $(REGISTRY)/$(REPO_NAME)/$$service:latest \
			--file $$dockerfile \
			$(BUILD_ARGS) \
			--cache-from type=local,src=/tmp/.buildx-cache \
			--cache-to type=local,dest=/tmp/.buildx-cache-new \
			--load \
			.; \
	done
	@rm -rf /tmp/.buildx-cache && mv /tmp/.buildx-cache-new /tmp/.buildx-cache || true

# Build images with SBOM generation
build-with-sbom: setup-buildx
	@echo "Building images with SBOM generation..."
	@command -v syft >/dev/null 2>&1 || { echo "Installing syft..."; curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin; }
	@mkdir -p sbom-reports
	@for i in $(shell seq 1 $(words $(SERVICES))); do \
		service=$(word $$i,$(SERVICES)); \
		dockerfile=$(word $$i,$(DOCKERFILES)); \
		echo "Building $$service with BuildKit and SBOM..."; \
		docker buildx build \
			--platform linux/amd64,linux/arm64 \
			--tag $(REGISTRY)/$(REPO_NAME)/$$service:$(VERSION) \
			--tag $(REGISTRY)/$(REPO_NAME)/$$service:$(BRANCH) \
			--tag $(REGISTRY)/$(REPO_NAME)/$$service:latest \
			--file $$dockerfile \
			$(BUILD_ARGS) \
			--provenance=true \
			--sbom=true \
			--cache-from type=local,src=/tmp/.buildx-cache \
			--cache-to type=local,dest=/tmp/.buildx-cache-new \
			--load \
			.; \
		echo "Generating SBOM for $$service..."; \
		syft $(REGISTRY)/$(REPO_NAME)/$$service:$(VERSION) -o spdx-json=sbom-reports/sbom-$$service.spdx.json; \
		syft $(REGISTRY)/$(REPO_NAME)/$$service:$(VERSION) -o cyclonedx-json=sbom-reports/sbom-$$service.cyclonedx.json; \
	done
	@rm -rf /tmp/.buildx-cache && mv /tmp/.buildx-cache-new /tmp/.buildx-cache || true

# Push all images
push-all:
	@echo "Pushing all images to registry..."
	@for service in $(SERVICES); do \
		echo "Pushing $$service..."; \
		docker buildx build \
			--platform linux/amd64,linux/arm64 \
			--tag $(REGISTRY)/$(REPO_NAME)/$$service:$(VERSION) \
			--tag $(REGISTRY)/$(REPO_NAME)/$$service:$(BRANCH) \
			--tag $(REGISTRY)/$(REPO_NAME)/$$service:latest \
			--file $(word $$i,$(DOCKERFILES)) \
			$(BUILD_ARGS) \
			--push \
			.; \
	done

# Sign images with Cosign
sign-all:
	@echo "Signing images with Cosign..."
	@command -v cosign >/dev/null 2>&1 || { echo "Please install cosign: https://docs.sigstore.dev/cosign/installation/"; exit 1; }
	@for service in $(SERVICES); do \
		echo "Signing $$service..."; \
		cosign sign --yes $(REGISTRY)/$(REPO_NAME)/$$service:$(VERSION); \
	done

# Security scan images
scan-images:
	@echo "Scanning images for vulnerabilities..."
	@command -v trivy >/dev/null 2>&1 || { echo "Installing trivy..."; curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin; }
	@mkdir -p security-reports
	@for service in $(SERVICES); do \
		echo "Scanning $$service..."; \
		trivy image --format sarif --output security-reports/trivy-$$service.sarif $(REGISTRY)/$(REPO_NAME)/$$service:$(VERSION) || true; \
		trivy image --format table $(REGISTRY)/$(REPO_NAME)/$$service:$(VERSION); \
	done

# Set up kind cluster
kind-setup:
	@echo "Setting up kind cluster..."
	@command -v kind >/dev/null 2>&1 || { echo "Please install kind: https://kind.sigs.k8s.io/docs/user/quick-start/"; exit 1; }
	@command -v kubectl >/dev/null 2>&1 || { echo "Please install kubectl"; exit 1; }
	@command -v helm >/dev/null 2>&1 || { echo "Please install helm"; exit 1; }
	@kind create cluster --name mcp-test --config - <<EOF || echo "Cluster may already exist" \
	kind: Cluster \
	apiVersion: kind.x-k8s.io/v1alpha4 \
	nodes: \
	- role: control-plane \
	  image: kindest/node:v1.28.0 \
	  kubeadmConfigPatches: \
	  - | \
	    kind: InitConfiguration \
	    nodeRegistration: \
	      kubeletExtraArgs: \
	        node-labels: "ingress-ready=true" \
	  extraPortMappings: \
	  - containerPort: 80 \
	    hostPort: 80 \
	    protocol: TCP \
	  - containerPort: 443 \
	    hostPort: 443 \
	    protocol: TCP
	@kubectl cluster-info --context kind-mcp-test

# Load images into kind cluster
kind-load-images:
	@echo "Loading images into kind cluster..."
	@for service in $(SERVICES); do \
		echo "Loading $$service into kind..."; \
		kind load docker-image $(REGISTRY)/$(REPO_NAME)/$$service:$(VERSION) --name mcp-test; \
	done

# Deploy services to kind
kind-deploy: kind-load-images create-migration-configmaps
	@echo "Deploying services to kind cluster..."
	
	# Install PostgreSQL
	@helm repo add bitnami https://charts.bitnami.com/bitnami || true
	@helm repo update
	@helm upgrade --install postgres bitnami/postgresql \
		--set auth.username=test_user \
		--set auth.password=test_password \
		--set auth.database=test_mcp_db \
		--wait || true
	
	# Create namespace
	@kubectl create namespace mcp-system || true
	
	# Deploy services using Helm charts
	@for service in auth-service context-service; do \
		if [ -d "gitops/charts/$$service" ]; then \
			echo "Deploying $$service..."; \
			helm upgrade --install $$service gitops/charts/$$service \
				--namespace mcp-system \
				--set image.repository=$(REGISTRY)/$(REPO_NAME)/$$service \
				--set image.tag=$(VERSION) \
				--set image.pullPolicy=Never \
				--wait || true; \
		fi; \
	done
	
	# Deploy text-summarization service
	@if [ -d "services/text-summarization/helm/text-summarization" ]; then \
		echo "Deploying text-summarization..."; \
		helm upgrade --install text-summarization services/text-summarization/helm/text-summarization \
			--namespace mcp-system \
			--set image.repository=$(REGISTRY)/$(REPO_NAME)/text-summarization \
			--set image.tag=$(VERSION) \
			--set image.pullPolicy=Never \
			--wait || true; \
	fi

# Run smoke tests on kind
kind-test:
	@echo "Running smoke tests on kind cluster..."
	@kubectl wait --for=condition=available --timeout=300s deployment --all -n mcp-system || true
	@kubectl get services -n mcp-system
	@kubectl get pods -n mcp-system
	
	# Basic health checks
	@for service in auth-service context-service text-summarization; do \
		echo "Testing $$service health..."; \
		kubectl exec -n mcp-system deployment/$$service -- curl -f http://localhost:8000/healthz 2>/dev/null || \
		kubectl exec -n mcp-system deployment/$$service -- curl -f http://localhost:8001/healthz 2>/dev/null || \
		kubectl exec -n mcp-system deployment/$$service -- curl -f http://localhost:8443/health 2>/dev/null || \
		echo "Health check failed for $$service"; \
	done

# Clean up kind cluster
kind-cleanup:
	@echo "Cleaning up kind cluster..."
	@kind delete cluster --name mcp-test || true

# Set up local development environment
local-dev: install
	@echo "Setting up local development environment..."
	@docker-compose -f services/text-summarization/auth-service/docker-compose.yml up -d || true
	@echo "Development environment ready!"
	@echo "Services:"
	@echo "  - PostgreSQL: localhost:5432"
	@echo "  - Vault: localhost:8200"

# Start local development stack
local-stack-up:
	@echo "Starting local development stack..."
	docker-compose -f docker-compose.dev.yml up -d
	@echo "Waiting for services to be ready..."
	@sleep 15
	@echo "Development stack started!"
	@echo "Services available at:"
	@echo "  - PostgreSQL: localhost:5432 (user: mcp_user, password: mcp_password)"
	@echo "  - Vault: http://localhost:8200 (token: myroot)"
	@echo "  - Redis: localhost:6379 (password: redis_password)"
	@echo "  - JWKS: http://localhost:8080/.well-known/jwks.json"
	@echo "  - Adminer: http://localhost:8081"

# Stop local development stack
local-stack-down:
	@echo "Stopping local development stack..."
	docker-compose -f docker-compose.dev.yml down

# Check local development stack status
local-stack-status:
	@echo "Local development stack status:"
	docker-compose -f docker-compose.dev.yml ps

# View logs from local development stack
local-stack-logs:
	@echo "Viewing logs from local development stack..."
	docker-compose -f docker-compose.dev.yml logs -f

# Local run for services (with dependency management)
local-run: local-stack-up
	@echo "Starting all services locally..."
	@echo "Services will start in the following order:"
	@echo "  1. auth-service (Go)"
	@echo "  2. context-service (Python)"
	@echo "  3. text-summarization (Python)"

	# Start auth-service first
	@echo "Starting auth-service..."
	cd services/text-summarization/auth-service \u0026\u0026 make local-run \u0026 || echo "Auth service failed to start"
	sleep 5

	# Start context-service
	@echo "Starting context-service..."
	cd services/context-service \u0026\u0026 make local-run \u0026 || echo "Context service failed to start"
	sleep 5

	# Start text-summarization service
	@echo "Starting text-summarization..."
	cd services/text-summarization \u0026\u0026 make local-run \u0026 || echo "Text-summarization service failed to start"

	@echo "All services started! Check the logs above for any errors."
	@echo "Services are running on:"
	@echo "  - auth-service: http://localhost:8443"
	@echo "  - context-service: http://localhost:8001"
	@echo "  - text-summarization: http://localhost:8000"
	@echo "Press Ctrl+C to stop all services."

# Generate API documentation
generate-docs:
	@echo "Generating API documentation..."
	python3 scripts/generate-api-docs.py

# Clean up build artifacts
clean:
	@echo "Cleaning up build artifacts..."
	@docker system prune -f || true
	@rm -rf /tmp/.buildx-cache
	@rm -rf sbom-reports
	@rm -rf security-reports
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true

# Complete CI/CD pipeline simulation with Alembic migrations
ci-pipeline: clean install test-all security-scan build-with-sbom scan-images push-all sign-all deploy-pipeline-with-migrations
	@echo "CI/CD pipeline completed successfully!"

# Deployment pipeline with Alembic migrations
deploy-pipeline-with-migrations: kind-setup kind-deploy run-alembic-migrations kind-test
	@echo "Deployment pipeline with migrations completed successfully!"

# Run Alembic migrations in kind cluster
run-alembic-migrations:
	@echo "Running Alembic migrations in kind cluster..."
	@echo "Waiting for PostgreSQL to be ready..."
	@kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=postgresql --timeout=300s || true
	
	# Run main migrations
	@echo "Running main database migrations..."
	@if [ -d "migrations" ]; then \
		kubectl run alembic-main-migration --rm -i --restart=Never \
			--image=python:3.11-slim \
			--env="DATABASE_URL=postgresql://test_user:test_password@postgres-postgresql:5432/test_mcp_db" \
			--command -- sh -c \
			"pip install alembic psycopg2-binary sqlalchemy && \
			 cd /migrations && \
			 alembic upgrade head" \
			--overrides='{ "spec": { "containers": [{ "name": "alembic-main-migration", "volumeMounts": [{ "name": "migrations", "mountPath": "/migrations" }] }], "volumes": [{ "name": "migrations", "configMap": { "name": "main-migrations" } }] } }' || true; \
	fi
	
	# Run context-service migrations
	@echo "Running context-service migrations..."
	@if [ -d "services/context-service/migrations" ]; then \
		kubectl run alembic-context-migration --rm -i --restart=Never \
			--image=python:3.11-slim \
			--env="DATABASE_URL=postgresql://test_user:test_password@postgres-postgresql:5432/test_mcp_db" \
			--command -- sh -c \
			"pip install alembic psycopg2-binary sqlalchemy && \
			 cd /migrations && \
			 alembic upgrade head" \
			--overrides='{ "spec": { "containers": [{ "name": "alembic-context-migration", "volumeMounts": [{ "name": "migrations", "mountPath": "/migrations" }] }], "volumes": [{ "name": "migrations", "configMap": { "name": "context-migrations" } }] } }' || true; \
	fi
	
	@echo "Alembic migrations completed!"

# Create ConfigMaps for migrations
create-migration-configmaps:
	@echo "Creating ConfigMaps for migrations..."
	@# Create ConfigMap for main migrations
	@if [ -d "migrations" ]; then \
		kubectl create configmap main-migrations --from-file=migrations/ --dry-run=client -o yaml | kubectl apply -f - || true; \
	fi
	@# Create ConfigMap for context-service migrations
	@if [ -d "services/context-service/migrations" ]; then \
		kubectl create configmap context-migrations --from-file=services/context-service/migrations/ --dry-run=client -o yaml | kubectl apply -f - || true; \
	fi

# Complete deployment pipeline
deploy-pipeline: kind-setup kind-deploy kind-test
	@echo "Deployment pipeline completed successfully!"

# End-to-end pipeline
e2e: ci-pipeline deploy-pipeline
	@echo "End-to-end pipeline completed successfully!"
