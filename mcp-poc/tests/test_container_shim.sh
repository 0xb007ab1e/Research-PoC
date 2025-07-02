#!/bin/bash

# Test script for container.sh

# Test if docker or podman is detected
./scripts/container.sh 2>&1 | grep -q "No container engine found"
if [ $? -eq 0 ]; then
    echo "Test failed: No container engine found"
    exit 1
fi

# Test build command - check for any build-related help
./scripts/container.sh build --help 2>&1 | grep -qi "build"
if [ $? -ne 0 ]; then
    echo "Test failed: build command"
    exit 1
fi

# Test run command - check for any run-related help
./scripts/container.sh run --help 2>&1 | grep -qi "run"
if [ $? -ne 0 ]; then
    echo "Test failed: run command"
    exit 1
fi

# Test compose command - check for any compose-related help
./scripts/container.sh compose --help 2>&1 | grep -qi "compose\|kube"
if [ $? -ne 0 ]; then
    echo "Test failed: compose command"
    exit 1
fi

# Test invalid command
test_output=$(./scripts/container.sh invalid 2>&1)
if [[ "$test_output" != "Unknown command: invalid" ]]; then
    echo "Test failed: invalid command"
    exit 1
fi

echo "All tests passed successfully!"

