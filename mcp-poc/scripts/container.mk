# Container Engine Detection and Configuration
# This file provides CONTAINER_CMD and COMPOSE_CMD variables for use in Makefiles
# Usage: include scripts/container.mk

# Default values for backward compatibility
CONTAINER_CMD ?= docker
COMPOSE_CMD ?= docker compose

# Detect available container engine and override defaults
CONTAINER_DETECTION := $(shell \
	if command -v docker > /dev/null 2>&1; then \
		echo "docker"; \
	elif command -v podman > /dev/null 2>&1; then \
		echo "podman"; \
	else \
		echo "none"; \
	fi)

# Override with detected values if available
ifeq ($(CONTAINER_DETECTION),docker)
	CONTAINER_CMD := docker
	COMPOSE_CMD := docker compose
else ifeq ($(CONTAINER_DETECTION),podman)
	CONTAINER_CMD := podman
	# Check if podman-compose is available
	PODMAN_COMPOSE_AVAILABLE := $(shell command -v podman-compose > /dev/null 2>&1 && echo "yes" || echo "no")
	ifeq ($(PODMAN_COMPOSE_AVAILABLE),yes)
		COMPOSE_CMD := podman-compose
	else
		COMPOSE_CMD := podman play kube
	endif
else ifeq ($(CONTAINER_DETECTION),none)
	# Keep defaults for backward compatibility when no container engine is detected
	# This allows the Makefile to still work in environments where the shim isn't needed
endif

# Export the variables for use in shell commands
export CONTAINER_CMD
export COMPOSE_CMD

# Print detection info (can be called with 'make container-info')
.PHONY: container-info
container-info:
	@echo "Container engine: $(CONTAINER_CMD)"
	@echo "Compose command: $(COMPOSE_CMD)"
	@echo "Detection result: $(CONTAINER_DETECTION)"
