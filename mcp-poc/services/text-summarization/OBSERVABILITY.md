# MCP Text Summarization Service - Observability & Monitoring

This document describes the comprehensive observability setup for the MCP Text Summarization Service, including structured logging, distributed tracing, and metrics collection.

## Overview

The service implements a complete observability stack with:

- **Structured JSON Logging** with `structlog`
- **Distributed Tracing** with OpenTelemetry and Jaeger
- **Metrics Collection** with Prometheus and OpenTelemetry
- **Log Aggregation** with Loki and Promtail
- **Visualization** with Grafana

## Components

### 1. Structured Logging (`structlog`)

#### Features
- JSON-formatted logs for easy parsing
- OpenTelemetry trace correlation
- Service context in all log entries
- Security event logging
- Performance metrics logging

#### Configuration
```python
from structured_logging import setup_structured_logging, get_logger

# Setup structured logging
setup_structured_logging()

# Get a logger with context
logger = get_logger(__name__, service="text-summarization")
```

#### Log Format Example
```json
{
  "timestamp": "2023-12-01T10:30:00.123456Z",
  "level": "info",
  "event": "Summarization completed successfully",
  "logger": "main",
  "service": {
    "name": "mcp-text-summarization",
    "version": "1.0.0",
    "environment": "production"
  },
  "trace_id": "1234567890abcdef1234567890abcdef",
  "span_id": "1234567890abcdef",
  "request_id": "req-uuid-here",
  "tenant_id": "tenant-123",
  "semantic_score": 0.85,
  "processing_time_ms": 1250,
  "model_used": "openai"
}
```

### 2. OpenTelemetry Integration

#### Distributed Tracing
- Automatic instrumentation of FastAPI requests
- Custom spans for summarization operations
- Trace context propagation using B3 format
- Export to in-cluster OTel collector

#### Configuration
```env
ENABLE_TELEMETRY=true
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_TRACE_SAMPLE_RATE=1.0
OTEL_METRICS_EXPORT_INTERVAL=30
```

#### Custom Metrics
- HTTP request counters and histograms
- Summarization operation metrics
- Semantic similarity score distributions
- Active request gauges
- Error counters by type

### 3. Prometheus Metrics

#### Available Metrics

**HTTP Metrics:**
- `http_requests_total` - Total HTTP requests by method, endpoint, status
- `http_request_duration_seconds` - Request duration histogram
- `active_requests` - Current active request count

**Summarization Metrics:**
- `summarizations_total` - Total summarizations by model and status
- `summarization_duration_seconds` - Processing time by model
- `semantic_similarity_score` - Distribution of similarity scores

**OpenTelemetry Metrics:**
- All HTTP and summarization metrics also exported via OTel
- Additional service metadata and trace correlation

### 4. Observability Stack Deployment

#### Using Docker Compose

```bash
# Start the complete observability stack
docker-compose -f docker-compose.observability.yml up -d

# View logs
docker-compose -f docker-compose.observability.yml logs -f text-summarization
```

#### Services and Ports

| Service | Port | Purpose |
|---------|------|---------|
| Text Summarization | 8000 | Main API |
| Prometheus Metrics | 9090 | Service metrics endpoint |
| OTel Collector | 4317 | OTLP gRPC receiver |
| OTel Collector | 4318 | OTLP HTTP receiver |
| Jaeger UI | 16686 | Distributed tracing UI |
| Prometheus | 9091 | Metrics database |
| Grafana | 3000 | Visualization dashboard |
| Loki | 3100 | Log aggregation |

### 5. Configuration Examples

#### Production Configuration
```env
ENVIRONMENT=production
LOG_LEVEL=WARNING
OTEL_TRACE_SAMPLE_RATE=0.1  # Sample 10% in production
OTEL_ENABLE_CONSOLE=false
ENABLE_METRICS=true
ENABLE_TELEMETRY=true
```

#### Development Configuration
```env
ENVIRONMENT=development
LOG_LEVEL=DEBUG
OTEL_TRACE_SAMPLE_RATE=1.0  # Sample all traces in dev
OTEL_ENABLE_CONSOLE=true
ENABLE_METRICS=true
ENABLE_TELEMETRY=true
```

## Monitoring Best Practices

### 1. Alerting Rules

**High Error Rate:**
```yaml
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
  for: 2m
  labels:
    severity: warning
  annotations:
    summary: "High error rate detected"
```

**Semantic Score Degradation:**
```yaml
- alert: LowSemanticScore
  expr: histogram_quantile(0.95, rate(semantic_similarity_score_bucket[5m])) < 0.7
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "Semantic similarity scores are degrading"
```

### 2. Dashboard Queries

**Request Rate:**
```promql
rate(http_requests_total[5m])
```

**Average Response Time:**
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

**Summarization Success Rate:**
```promql
rate(summarizations_total{status="success"}[5m]) / rate(summarizations_total[5m])
```

### 3. Log Analysis

**Find all errors with trace context:**
```json
{
  "level": "error",
  "trace_id": "1234567890abcdef1234567890abcdef"
}
```

**Performance analysis:**
```json
{
  "performance": {
    "operation": "summarization",
    "duration_ms": "> 5000",
    "status": "success"
  }
}
```

## Troubleshooting

### Common Issues

1. **OTel Collector Connection Issues**
   - Check network connectivity: `docker network ls`
   - Verify collector endpoint: `OTEL_EXPORTER_OTLP_ENDPOINT`
   - Check collector logs: `docker-compose logs otel-collector`

2. **Missing Traces in Jaeger**
   - Verify trace sampling rate: `OTEL_TRACE_SAMPLE_RATE`
   - Check span export configuration
   - Ensure B3 propagation headers are present

3. **Metrics Not Appearing**
   - Check Prometheus targets: `http://localhost:9091/targets`
   - Verify metrics endpoint: `http://localhost:9090/metrics`
   - Check OTel metrics pipeline configuration

### Debug Commands

```bash
# Check service metrics
curl http://localhost:9090/metrics

# Check OTel collector health
curl http://localhost:13133/

# View structured logs
docker-compose logs text-summarization | jq '.'

# Check trace propagation
curl -H "traceparent: 00-1234567890abcdef1234567890abcdef-1234567890abcdef-01" \
     http://localhost:8000/v1/summarize
```

## Security Considerations

1. **Sensitive Data in Logs**
   - API keys and tokens are automatically masked
   - PII data should be excluded from traces
   - Use structured logging helpers for consistent sanitization

2. **Metrics Exposure**
   - Metrics endpoints should be secured in production
   - Consider network-level access controls
   - Monitor for information disclosure in metric labels

3. **Trace Data**
   - Limit trace retention periods
   - Ensure trace data doesn't contain sensitive information
   - Use sampling to reduce data volume in production

## Performance Impact

- **Logging:** Minimal overhead with structured logging
- **Tracing:** ~1-5% overhead depending on sampling rate
- **Metrics:** Negligible overhead for counter/histogram operations
- **Memory:** OTel uses batching to minimize memory usage

## Integration with Kubernetes

For Kubernetes deployments, update the OTel endpoint:

```env
OTEL_EXPORTER_OTLP_ENDPOINT=http://opentelemetry-collector.observability.svc.cluster.local:4317
```

Use Kubernetes service discovery for Prometheus:

```yaml
kubernetes_sd_configs:
  - role: pod
    namespaces:
      names:
        - default
```

## Next Steps

1. Set up Grafana dashboards for key metrics
2. Configure alerting rules in Prometheus
3. Implement log-based alerts in Loki
4. Set up trace-based SLO monitoring
5. Configure long-term storage for metrics and traces
