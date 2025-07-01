.PHONY: build test clean docker-build docker-up docker-down lint

# Go parameters
GOCMD=go
GOBUILD=$(GOCMD) build
GOCLEAN=$(GOCMD) clean
GOTEST=$(GOCMD) test
GOGET=$(GOCMD) get
GOMOD=$(GOCMD) mod
BINARY_NAME=auth-service
MAIN_PATH=./cmd/server

# Build the binary
build:
	$(GOBUILD) -o $(BINARY_NAME) $(MAIN_PATH)

# Build for linux
build-linux:
	CGO_ENABLED=0 GOOS=linux GOARCH=amd64 $(GOBUILD) -ldflags='-w -s -extldflags "-static"' -a -installsuffix cgo -o $(BINARY_NAME) $(MAIN_PATH)

# Run tests
test:
	$(GOTEST) -v ./...

# Run tests with coverage
test-coverage:
	$(GOTEST) -cover ./...

# Clean build artifacts
clean:
	$(GOCLEAN)
	rm -f $(BINARY_NAME)

# Download dependencies
deps:
	$(GOMOD) download
	$(GOMOD) tidy

# Run linter
lint:
	golangci-lint run

# Build Docker image
docker-build:
	docker build -t $(BINARY_NAME):latest .

# Start services with Docker Compose
docker-up:
	docker-compose up -d

# Stop services with Docker Compose
docker-down:
	docker-compose down

# Start services and view logs
docker-logs:
	docker-compose up

# Run the service locally (requires Vault to be running)
run:
	$(GOBUILD) -o $(BINARY_NAME) $(MAIN_PATH) && ./$(BINARY_NAME)

# Ensure compose stack is up
ensure-stack:
	@echo "Checking if development stack is running..."
	@docker-compose -f ../../../docker-compose.dev.yml ps | grep -q "Up" || { \
		echo "Starting development stack..."; \
		docker-compose -f ../../../docker-compose.dev.yml up -d; \
		echo "Waiting for services to be ready..."; \
		sleep 15; \
	}

# Run service locally for development
local-run: deps ensure-stack
	@echo "Setting up environment variables..."
	@export DB_HOST=localhost && \
	export DB_PORT=5432 && \
	export DB_NAME=auth_service && \
	export DB_USER=auth_service_user && \
	export DB_PASSWORD=auth_service_password && \
	export VAULT_ADDR=http://localhost:8200 && \
	export VAULT_TOKEN=myroot && \
	export REDIS_URL=redis://:redis_password@localhost:6379/2 && \
	export ENVIRONMENT=development && \
	export DEBUG=true && \
	export PORT=8443 && \
	echo "Building auth service..." && \
	$(GOBUILD) -o $(BINARY_NAME) $(MAIN_PATH) && \
	echo "Starting auth service with hot-reload (using air)..." && \
	command -v air >/dev/null 2>&1 && air || { \
		echo "air not found, starting without hot-reload..."; \
		./$(BINARY_NAME); \
	}

# Development setup - start Vault and run service
dev: docker-up
	sleep 10
	$(MAKE) run

# Help
help:
	@echo "Available targets:"
	@echo "  build         - Build the binary"
	@echo "  build-linux   - Build for Linux (static binary)"
	@echo "  test          - Run tests"
	@echo "  test-coverage - Run tests with coverage"
	@echo "  clean         - Clean build artifacts"
	@echo "  deps          - Download and tidy dependencies"
	@echo "  lint          - Run linter"
	@echo "  docker-build  - Build Docker image"
	@echo "  docker-up     - Start services with Docker Compose"
	@echo "  docker-down   - Stop services with Docker Compose"
	@echo "  docker-logs   - Start services and view logs"
	@echo "  run           - Run the service locally"
	@echo "  dev           - Development setup (Vault + service)"
	@echo "  help          - Show this help message"
