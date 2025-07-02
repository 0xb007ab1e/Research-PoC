#!/bin/bash

# Build script for MCP Text Summarization Service
# This script builds the Docker image with proper security configurations

set -euo pipefail

# Configuration
IMAGE_NAME="gcr.io/your-project/text-summarization-service"
VERSION="${VERSION:-1.0.0}"
BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ')
VCS_REF=$(git rev-parse HEAD 2>/dev/null || echo "unknown")

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building MCP Text Summarization Service${NC}"
echo "Image: ${IMAGE_NAME}:${VERSION}"
echo "Build Date: ${BUILD_DATE}"
echo "VCS Ref: ${VCS_REF}"
echo

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build \
  --build-arg BUILD_DATE="${BUILD_DATE}" \
  --build-arg VERSION="${VERSION}" \
  --build-arg VCS_REF="${VCS_REF}" \
  --tag "${IMAGE_NAME}:${VERSION}" \
  --tag "${IMAGE_NAME}:latest" \
  .

echo -e "${GREEN}✓ Docker image built successfully${NC}"

# Run basic security checks
echo -e "${YELLOW}Running security checks...${NC}"

# Check if container runs as non-root
USER_CHECK=$(docker run --rm "${IMAGE_NAME}:${VERSION}" /usr/bin/id -u 2>/dev/null || echo "failed")
if [ "$USER_CHECK" = "1000" ]; then
  echo -e "${GREEN}✓ Container runs as UID 1000${NC}"
else
  echo -e "${RED}✗ Container does not run as UID 1000 (got: $USER_CHECK)${NC}"
fi

# Check for distroless image
IMAGE_LAYERS=$(docker history "${IMAGE_NAME}:${VERSION}" --format "table {{.CreatedBy}}" | grep -c "distroless" || echo "0")
if [ "$IMAGE_LAYERS" -gt "0" ]; then
  echo -e "${GREEN}✓ Using distroless base image${NC}"
else
  echo -e "${YELLOW}! Could not verify distroless base image${NC}"
fi

# Test basic container functionality
echo -e "${YELLOW}Testing container startup...${NC}"
CONTAINER_ID=$(docker run -d -p 8001:8000 "${IMAGE_NAME}:${VERSION}")

# Wait for container to start
sleep 5

# Check if health endpoint responds
if curl -f -s http://localhost:8001/healthz > /dev/null 2>&1; then
  echo -e "${GREEN}✓ Health check endpoint responding${NC}"
else
  echo -e "${RED}✗ Health check endpoint not responding${NC}"
  docker logs "$CONTAINER_ID"
fi

# Clean up test container
docker stop "$CONTAINER_ID" > /dev/null 2>&1
docker rm "$CONTAINER_ID" > /dev/null 2>&1

echo
echo -e "${GREEN}Build completed successfully!${NC}"
echo
echo "To push to registry:"
echo "  docker push ${IMAGE_NAME}:${VERSION}"
echo
echo "To deploy with Helm:"
echo "  helm install text-summarization ./helm/text-summarization \\"
echo "    --set image.repository=${IMAGE_NAME} \\"
echo "    --set image.tag=${VERSION}"
