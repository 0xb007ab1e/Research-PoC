# Multi-stage build for better security and smaller image size
# Stage 1: Build stage with full Python environment
FROM python:3.11-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user for security
RUN groupadd -r contextservice && useradd -r -g contextservice contextservice

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and set permissions
RUN mkdir -p /var/log/contextservice && \
    chown -R contextservice:contextservice /app /var/log/contextservice

# Remove unnecessary files
RUN find . -type f -name "*.pyc" -delete && \
    find . -type d -name "__pycache__" -delete && \
    rm -rf .git .pytest_cache .coverage tests/ *.md

# Stage 2: Production stage with distroless image
FROM gcr.io/distroless/python3:latest

# Set runtime labels
LABEL stage="production" \
      maintainer="MCP Team" \
      org.opencontainers.image.title="MCP Context Service" \
      org.opencontainers.image.description="Context management service with semantic validation"

# Copy CA certificates from builder (includes system CA bundle)
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /usr/share/ca-certificates/ /usr/share/ca-certificates/

# Copy Python packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code from builder with proper ownership for UID 1000
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
    CMD ["/usr/local/bin/python", "-c", "import httpx; httpx.get('http://localhost:8001/healthz', timeout=5)"] \
    || exit 1

# Expose port
EXPOSE 8001

# Run the application
ENTRYPOINT ["/usr/local/bin/python", "main.py"]
