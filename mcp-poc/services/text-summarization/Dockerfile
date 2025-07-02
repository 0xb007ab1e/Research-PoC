# Multi-stage build for MCP Text Summarization Service
# Stage 1: Build stage with full Python environment
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION=1.0.0
ARG VCS_REF

# Add labels for better container management
LABEL maintainer="MCP Team" \
      org.opencontainers.image.title="MCP Text Summarization Service" \
      org.opencontainers.image.description="AI-powered text summarization with semantic validation" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/your-org/mcp-poc"

# Install system dependencies needed for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    pip check

# Copy application source code
COPY . .

# Remove unnecessary files
RUN find . -type f -name "*.pyc" -delete && \
    find . -type d -name "__pycache__" -delete && \
    rm -rf .git .pytest_cache .coverage tests/ *.md

# Stage 2: Production stage with minimal distroless image
FROM gcr.io/distroless/python3:latest

# Set runtime labels
LABEL stage="production" \
      security.hardened="true" \
      ca.bundle.included="true"

# Copy CA certificates from builder (includes system CA bundle for TLS/mTLS)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/ca-certificates/ /usr/share/ca-certificates/

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code from builder with proper ownership for UID 1000
# Note: We'll set the USER directive in Kubernetes securityContext to ensure UID 1000
COPY --from=builder --chown=1000:1000 /app /app

# Set working directory
WORKDIR /app

# Set environment variables for security and CA certificates
ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    LANG=C.UTF-8 \
    TZ=UTC \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    SSL_CERT_DIR=/etc/ssl/certs \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD ["/usr/local/bin/python", "-c", "import requests; requests.get('http://localhost:8000/healthz', timeout=5)"] \
    || exit 1

# Expose port
EXPOSE 8000

# Set read-only root filesystem (handled at runtime by securityContext)
# Run the application
ENTRYPOINT ["/usr/local/bin/python", "-m", "uvicorn", "main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
