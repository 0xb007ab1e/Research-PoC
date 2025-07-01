# Container Environment Variables
# This file exports CONTAINER_CMD and COMPOSE_CMD variables for use in Makefiles
# Usage: include scripts/container-env.mk

# Detect container engine and set variables
CONTAINER_DETECTION := $(shell \
	if command -v docker >/dev/null 2>&1; then \
		echo "docker"; \
	elif command -v podman >/dev/null 2>&1; then \
		echo "podman"; \
	else \
		echo "none"; \
	fi)

# Set CONTAINER_CMD based on detection
ifeq ($(CONTAINER_DETECTION),docker)
	CONTAINER_CMD := docker
	COMPOSE_CMD := docker compose
else ifeq ($(CONTAINER_DETECTION),podman)
	CONTAINER_CMD := podman
	# Check if podman-compose is available
	PODMAN_COMPOSE_AVAILABLE := $(shell command -v podman-compose >/dev/null 2>&1 && echo "yes" || echo "no")
	ifeq ($(PODMAN_COMPOSE_AVAILABLE),yes)
		COMPOSE_CMD := podman-compose
	else
		COMPOSE_CMD := podman play kube
	endif
else
	$(error No container engine found! Please install Docker or Podman)
endif

# Export the variables
export CONTAINER_CMD
export COMPOSE_CMD

# Print detection info (can be called with 'make container-info')
.PHONY: container-info
container-info:
	@echo "Container engine: $(CONTAINER_CMD)"
	@echo "Compose command: $(COMPOSE_CMD)"
