#!/bin/bash

# Detect available container engine
if command -v docker &> /dev/null
then
    CONTAINER_CMD="docker"
    COMPOSE_CMD="docker compose"
elif command -v podman &> /dev/null
then
    CONTAINER_CMD="podman"
    if command -v podman-compose &> /dev/null
    then
        COMPOSE_CMD="podman-compose"
    else
        COMPOSE_CMD="podman play kube"
    fi
else
    echo "No container engine found! Please install Docker or Podman." >&2
    exit 1
fi

export CONTAINER_CMD
export COMPOSE_CMD

# If sourced, just export the variables
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    return 0
fi

# Mirror Docker CLI calls
case "$1" in
    build|run|login|push)
        exec $CONTAINER_CMD "$@"
        ;;
    compose)
        shift
        exec $COMPOSE_CMD "$@"
        ;;
    "")
        echo "Unknown command: " >&2
        exit 1
        ;;
    *)
        echo "Unknown command: $1" >&2
        exit 1
        ;;
esac

