# Container Engine Shim (`container.sh`)

A unified container engine wrapper that provides seamless compatibility between Docker and Podman.

## Features

- **Auto-detection**: Automatically detects available container engines in priority order: Docker → Podman
- **Unified Interface**: Provides consistent command-line interface regardless of underlying engine
- **Environment Export**: Exports `CONTAINER_CMD` and `COMPOSE_CMD` environment variables for downstream scripts and Makefiles
- **Compose Support**: Intelligently handles compose operations:
  - Uses `docker compose` when Docker is available
  - Falls back to `podman-compose` when Podman is available and `podman-compose` is installed
  - Falls back to `podman play kube` when only Podman is available

## Usage

### Direct Execution

```bash
# Build an image
./scripts/container.sh build -t myapp .

# Run a container
./scripts/container.sh run -it --rm ubuntu bash

# Use compose
./scripts/container.sh compose up -d

# Login to registry
./scripts/container.sh login registry.example.com

# Push image
./scripts/container.sh push myapp:latest
```

### Environment Variable Export

Source the script to export environment variables for use in other scripts:

```bash
# Source the script
source scripts/container.sh

# Use the exported variables
echo "Container engine: $CONTAINER_CMD"
echo "Compose command: $COMPOSE_CMD"

# Use in Makefiles
$CONTAINER_CMD build -t myapp .
$COMPOSE_CMD up -d
```

### Makefile Integration

```makefile
# Include at the top of your Makefile
include scripts/container-env.mk

# Use the variables
build:
	$(CONTAINER_CMD) build -t myapp .

up:
	$(COMPOSE_CMD) up -d

down:
	$(COMPOSE_CMD) down
```

## Supported Commands

- `build` - Build container images
- `run` - Run containers
- `compose` - Container orchestration
- `login` - Registry authentication
- `push` - Push images to registry

## Engine Detection Priority

1. **Docker** - If `docker` command is available
2. **Podman** - If `podman` command is available
3. **Error** - If no container engine is found

## Compose Command Selection

- **Docker**: Uses `docker compose` (modern Docker Compose V2)
- **Podman with podman-compose**: Uses `podman-compose` for Docker Compose compatibility
- **Podman only**: Uses `podman play kube` for Kubernetes-style orchestration

## Testing

Run the test suite to verify functionality:

```bash
# Python tests (comprehensive)
python3 tests/test_container_shim.py

# Bash tests (basic functionality)
tests/test_container_shim.sh
```

## Environment Variables

After sourcing or running the script, the following environment variables are available:

- `CONTAINER_CMD` - The detected container engine command (`docker` or `podman`)
- `COMPOSE_CMD` - The appropriate compose command for the detected engine

## Error Handling

The script will exit with code 1 and display an error message if:
- No container engine is found
- An unsupported command is used
- Command execution fails

## Examples

### Development Workflow

```bash
# Source the container environment
source scripts/container.sh

# Build your application
$CONTAINER_CMD build -t myapp:dev .

# Start development environment
$COMPOSE_CMD -f docker-compose.dev.yml up -d

# Run tests in container
$CONTAINER_CMD run --rm myapp:dev npm test

# Stop development environment
$COMPOSE_CMD -f docker-compose.dev.yml down
```

### CI/CD Integration

```bash
#!/bin/bash
set -e

# Detect and configure container engine
source scripts/container.sh

# Build and test
$CONTAINER_CMD build -t myapp:$BUILD_ID .
$CONTAINER_CMD run --rm myapp:$BUILD_ID npm test

# Deploy if tests pass
if [ "$?" = "0" ]; then
    $CONTAINER_CMD tag myapp:$BUILD_ID myapp:latest
    $CONTAINER_CMD push myapp:latest
fi
```
