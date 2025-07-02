# Container Shim Integration

This document describes how the Makefiles have been refactored to use the container shim for automatic detection and switching between Docker and Podman.

## Overview

All Makefiles in the project now use configurable container commands instead of hard-coded `docker` and `docker-compose` commands. This enables seamless switching between Docker, Podman, and other container engines.

## Implementation

### Core Configuration

Each Makefile now includes the following header:

```make
# Container command configuration
CONTAINER_CMD ?= docker
COMPOSE_CMD ?= docker compose
include scripts/container.mk   # auto-overrides if shim present
```

### Variable Usage

All container operations now use these variables:
- `$(CONTAINER_CMD)` instead of `docker`
- `$(COMPOSE_CMD)` instead of `docker-compose` or `docker compose`

### Affected Makefiles

1. **Main Makefile** (`/Makefile`)
   - All build targets (`build-all`, `build-with-sbom`, `push-all`)
   - Development stack commands (`local-stack-*`)
   - GitHub CLI integration
   - Clean-up operations

2. **Context Service** (`/services/context-service/Makefile`)
   - Docker build commands
   - Development stack management
   - Added `container-info` target

3. **Text Summarization** (`/services/text-summarization/Makefile`)
   - Docker build and scan commands
   - Development stack management
   - Added `container-info` target

4. **Auth Service** (`/services/text-summarization/auth-service/Makefile`)
   - Docker Compose operations
   - Development stack management
   - Added `container-info` target

## Container Shim (`scripts/container.mk`)

The shim automatically detects available container engines and sets appropriate commands:

### Detection Logic
1. **Docker**: Uses `docker` and `docker compose`
2. **Podman**: Uses `podman` and either:
   - `podman-compose` (if available)
   - `podman play kube` (fallback)
3. **Fallback**: Maintains backward compatibility with default values

### Features
- Automatic detection of available container engines
- Backward compatibility when no shim is present
- Environment variable export for shell commands
- `container-info` target for debugging detection

## Usage Examples

### Check Container Detection
```bash
make container-info
```

### Build All Services
```bash
make build-all
```

### Start Development Stack
```bash
make local-stack-up
```

### Service-Level Operations
```bash
cd services/context-service
make docker-build
make container-info
```

## Backward Compatibility

The implementation maintains full backward compatibility:
- Default values are set to standard Docker commands
- Works in environments without the shim
- Existing scripts and workflows continue to function
- No breaking changes to existing APIs

## Benefits

1. **Flexibility**: Support for multiple container engines
2. **Automatic Detection**: No manual configuration required
3. **Consistency**: Unified approach across all services
4. **Maintainability**: Centralized container command management
5. **Future-Proof**: Easy to add support for new container engines

## Testing

All targets have been tested with dry-run mode:
```bash
make build-all --dry-run
make push-all --dry-run
make local-stack-status --dry-run
```

The implementation correctly substitutes container commands and maintains proper shell variable expansion.
