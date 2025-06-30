# Multi-Tenant API & Data Segregation Design

## Overview

This document outlines the multi-tenant architecture design for the MCP (Model Context Protocol) system, ensuring secure tenant isolation, scalable API design, and efficient provisioning workflows.

## API Surface

### OpenAPI 3.1 Specification

The API is designed using OpenAPI 3.1 with custom extensions to support multi-tenancy:

```yaml
openapi: 3.1.0
info:
  title: MCP Multi-Tenant API
  version: 1.0.0
  description: Multi-tenant API with data segregation

servers:
  - url: https://api.mcp.example.com/v1
    description: Production API

paths:
  /tenants/{tenantId}/models:
    get:
      summary: List models for tenant
      x-tenant-scope: read
      parameters:
        - name: tenantId
          in: path
          required: true
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: List of models
          
  /tenants/{tenantId}/models/{modelId}/execute:
    post:
      summary: Execute model
      x-tenant-scope: execute
      parameters:
        - name: tenantId
          in: path
          required: true
          schema:
            type: string
            format: uuid
        - name: modelId
          in: path
          required: true
          schema:
            type: string
      responses:
        '200':
          description: Execution result

components:
  securitySchemes:
    TenantAuth:
      type: http
      scheme: bearer
      x-tenant-validation: true
```

### URI Versioning Strategy

All API endpoints follow the versioned URI pattern:
- Base pattern: `/v1/tenants/{tenantId}/...`
- Version in URI ensures backward compatibility
- Tenant ID is mandatory for all tenant-scoped operations
- Administrative endpoints use `/v1/admin/...` pattern

### Custom Extensions

- `x-tenant-scope`: Defines the required tenant permission level
  - `read`: Read-only access to tenant data
  - `write`: Write access to tenant data
  - `execute`: Execute operations within tenant context
  - `admin`: Administrative operations on tenant

## Isolation Guarantees

### Database Isolation

**PostgreSQL Schema-Based Isolation:**

```sql
-- Tenant schema creation
CREATE SCHEMA tenant_550e8400_e29b_41d4_a716_446655440000;

-- Connection-level isolation
SET search_path TO tenant_550e8400_e29b_41d4_a716_446655440000;

-- Disable RLS for performance (schema isolation provides security)
ALTER TABLE tenant_models DISABLE ROW LEVEL SECURITY;
```

**Implementation Details:**
- Each tenant gets a dedicated PostgreSQL schema
- Connection pools maintain tenant context via `search_path`
- Schema names use format: `tenant_<uuid_with_underscores>`
- Row-Level Security (RLS) is disabled in favor of schema isolation for performance
- Cross-tenant queries are prevented at the application layer

**Connection Pool Configuration:**
```python
# Tenant-aware connection pool
class TenantConnectionPool:
    def get_connection(self, tenant_id: str):
        conn = self.pool.get_connection()
        conn.execute(f"SET search_path TO tenant_{tenant_id.replace('-', '_')}")
        return conn
```

### Cache Isolation

**Redis Key Prefixing:**

```python
# Cache key structure
cache_key = f"{tenant_id}:models:{model_id}"
cache_key = f"{tenant_id}:sessions:{session_id}"
cache_key = f"{tenant_id}:results:{execution_id}"

# Example implementation
class TenantCache:
    def __init__(self, redis_client, tenant_id):
        self.redis = redis_client
        self.tenant_prefix = f"{tenant_id}:"
    
    def get(self, key: str):
        return self.redis.get(f"{self.tenant_prefix}{key}")
    
    def set(self, key: str, value, ttl=3600):
        return self.redis.setex(f"{self.tenant_prefix}{key}", ttl, value)
```

**Cache Isolation Features:**
- All Redis keys prefixed with `{tenantId}:`
- Automatic key expiration per tenant
- Memory usage monitoring per tenant
- Cache eviction policies respect tenant boundaries

### File/Object Storage Isolation

**S3 Bucket Policy:**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TenantIsolation",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:role/mcp-tenant-${aws:RequestedRegion}"
      },
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::mcp-${tenant.id}/*",
      "Condition": {
        "StringEquals": {
          "s3:ExistingObjectTag/tenant": "${tenant.id}"
        }
      }
    }
  ]
}
```

**Storage Structure:**
```
s3://mcp-550e8400-e29b-41d4-a716-446655440000/
├── models/
│   ├── model-v1.0.pkl
│   └── model-v1.1.pkl
├── data/
│   ├── training/
│   └── inference/
└── logs/
    └── execution/
```

## Tenant Provisioning Flow

### 1. Admin Tenant Creation

```http
POST /v1/admin/tenants
Authorization: Bearer <admin-token>
Content-Type: application/json

{
  "name": "Acme Corp",
  "plan": "enterprise",
  "region": "us-east-1",
  "admin_email": "admin@acme.com"
}
```

**Response:**
```json
{
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "provisioning",
  "provisioning_job_id": "job_123456"
}
```

### 2. Asynchronous Provisioning via Job Queue

**Job Queue Implementation (using Celery):**

```python
@celery.task(bind=True)
def provision_tenant(self, tenant_data):
    tenant_id = tenant_data['tenant_id']
    
    try:
        # Step 1: Database schema creation
        create_tenant_schema(tenant_id)
        
        # Step 2: Trigger Terraform Cloud
        terraform_run = trigger_terraform_provisioning(tenant_data)
        
        # Step 3: Wait for infrastructure
        wait_for_terraform_completion(terraform_run['id'])
        
        # Step 4: Initialize tenant data
        initialize_tenant_defaults(tenant_id)
        
        # Step 5: Create API keys
        api_keys = generate_tenant_api_keys(tenant_id)
        
        # Step 6: Send welcome email
        send_tenant_welcome_email(tenant_data, api_keys)
        
        # Step 7: Update status
        update_tenant_status(tenant_id, 'active')
        
        return {'status': 'completed', 'tenant_id': tenant_id}
        
    except Exception as e:
        # Cleanup on failure
        cleanup_failed_tenant(tenant_id)
        raise self.retry(countdown=60, max_retries=3)
```

### 3. Terraform Cloud Integration

**Terraform Workspace Configuration:**

```hcl
# terraform/tenant-module/main.tf
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.0"
    }
  }
}

variable "tenant_id" {
  description = "Unique tenant identifier"
  type        = string
}

variable "tenant_name" {
  description = "Human readable tenant name"
  type        = string
}

# S3 Bucket for tenant data
resource "aws_s3_bucket" "tenant_bucket" {
  bucket = "mcp-${var.tenant_id}"
  
  tags = {
    Tenant = var.tenant_id
    Name   = var.tenant_name
  }
}

# IAM Role for tenant operations
resource "aws_iam_role" "tenant_role" {
  name = "mcp-tenant-${var.tenant_id}"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# PostgreSQL Schema
resource "postgresql_schema" "tenant_schema" {
  name  = "tenant_${replace(var.tenant_id, "-", "_")}"
  owner = "mcp_app"
}

# Secrets Manager entries
resource "aws_secretsmanager_secret" "tenant_secrets" {
  name = "mcp/tenant/${var.tenant_id}"
  
  tags = {
    Tenant = var.tenant_id
  }
}

resource "aws_secretsmanager_secret_version" "tenant_secrets" {
  secret_id = aws_secretsmanager_secret.tenant_secrets.id
  secret_string = jsonencode({
    api_key = random_password.api_key.result
    webhook_secret = random_password.webhook_secret.result
  })
}

resource "random_password" "api_key" {
  length  = 32
  special = true
}

resource "random_password" "webhook_secret" {
  length  = 16
  special = false
}
```

### 4. Audit Logging to Loki

**Audit Event Structure:**

```python
import logging
from datetime import datetime
import json

class AuditLogger:
    def __init__(self, loki_url: str):
        self.loki_url = loki_url
        
    def log_tenant_event(self, event_type: str, tenant_id: str, details: dict):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "tenant_id": tenant_id,
            "details": details,
            "source": "tenant-provisioning"
        }
        
        # Send to Loki
        self.send_to_loki({
            "streams": [{
                "stream": {
                    "job": "mcp-audit",
                    "tenant_id": tenant_id,
                    "event_type": event_type
                },
                "values": [[
                    str(int(datetime.utcnow().timestamp() * 1000000000)),
                    json.dumps(log_entry)
                ]]
            }]
        })

# Usage in provisioning flow
audit_logger = AuditLogger("https://loki.monitoring.example.com")

audit_logger.log_tenant_event(
    "tenant_provisioning_started",
    tenant_id,
    {
        "admin_user": "admin@example.com",
        "tenant_name": "Acme Corp",
        "plan": "enterprise"
    }
)
```

**Loki Query Examples:**

```logql
# All tenant provisioning events
{job="mcp-audit", event_type="tenant_provisioning_started"}

# Failed provisioning events
{job="mcp-audit", event_type="tenant_provisioning_failed"}

# Events for specific tenant
{job="mcp-audit", tenant_id="550e8400-e29b-41d4-a716-446655440000"}
```

## Load Testing Specifications

### Test Environment Setup

**Load Test Configuration:**

```python
# locustfile.py
from locust import HttpUser, task, between
import uuid
import random

class TenantUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Simulate 500 concurrent tenants
        self.tenant_id = f"tenant-{random.randint(1, 500):03d}"
        self.auth_header = {"Authorization": f"Bearer {self.get_tenant_token()}"}
    
    @task(3)
    def list_models(self):
        self.client.get(
            f"/v1/tenants/{self.tenant_id}/models",
            headers=self.auth_header,
            name="list_models"
        )
    
    @task(2)
    def execute_model(self):
        model_id = f"model-{random.randint(1, 10)}"
        self.client.post(
            f"/v1/tenants/{self.tenant_id}/models/{model_id}/execute",
            json={"input": "test data"},
            headers=self.auth_header,
            name="execute_model"
        )
    
    @task(1)
    def get_execution_status(self):
        execution_id = str(uuid.uuid4())
        self.client.get(
            f"/v1/tenants/{self.tenant_id}/executions/{execution_id}",
            headers=self.auth_header,
            name="get_execution_status"
        )
```

### Performance Targets

**SLA Requirements:**

| Metric | Target | Measurement |
|--------|--------|-------------|
| P95 Latency | < 500ms | Per tenant, 500 concurrent tenants |
| P99 Latency | < 1000ms | Per tenant, 500 concurrent tenants |
| Throughput | > 1000 RPS | Across all tenants |
| Error Rate | < 0.1% | 4xx/5xx responses |
| Memory Usage | < 8GB | Per application instance |

### Load Test Results

**Test Execution:**

```bash
# Run load test with 500 concurrent users (tenants)
locust -f locustfile.py --host=https://api.mcp.example.com \
       --users=500 --spawn-rate=10 --run-time=10m \
       --html=load-test-report.html
```

**Expected Results:**

```
Type     Name                                   # reqs    # fails  |    Avg    Min    Max  Median  |   req/s failures/s
---------|--------------------------------------|----------|--------|-------|-------|-------|--------|--------|---------
GET      list_models                              15000        0  |    245     12    489     240  |   25.0    0.00
POST     execute_model                            10000        0  |    387     45    498     380  |   16.7    0.00
GET      get_execution_status                      5000        0  |    123      8    245     120  |    8.3    0.00
---------|--------------------------------------|----------|--------|-------|-------|-------|--------|--------|---------
         Aggregated                               30000        0  |    285      8    498     280  |   50.0    0.00

Response time percentiles (approximated):
 Type     Name                                      50%    66%    75%    80%    90%    95%    98%    99%  99.9% 99.99%   100% # reqs
---------|----------------------------------------|------|------|------|------|------|------|------|------|------|------|------|------
 GET      list_models                               240    280    320    340    380    420    460    480    489    489    489  15000
 POST     execute_model                             380    410    440    450    470    485    495    498    498    498    498  10000
 GET      get_execution_status                      120    140    160    170    190    210    230    240    245    245    245   5000
---------|----------------------------------------|------|------|------|------|------|------|------|------|------|------|------|------
         Aggregated                                280    320    360    380    420    450    480    490    495    498    498  30000
```

### Monitoring and Observability

**Grafana Dashboard Metrics:**

```yaml
# grafana-dashboard.yml
dashboard:
  title: "Multi-Tenant Performance"
  panels:
    - title: "P95 Latency by Tenant"
      type: "graph"
      targets:
        - expr: 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{job="mcp-api"}[5m])) by (tenant_id)'
          legendFormat: "{{tenant_id}}"
    
    - title: "Requests per Second by Tenant"
      type: "graph"
      targets:
        - expr: 'rate(http_requests_total{job="mcp-api"}[5m]) by (tenant_id)'
          legendFormat: "{{tenant_id}}"
    
    - title: "Database Connection Pool Usage"
      type: "graph"
      targets:
        - expr: 'pg_pool_connections_active by (tenant_schema)'
          legendFormat: "{{tenant_schema}}"
```

## Security Considerations

### Tenant Data Protection

1. **Encryption at Rest**: All tenant data encrypted using AES-256
2. **Encryption in Transit**: TLS 1.3 for all API communications
3. **Key Management**: AWS KMS with tenant-specific keys
4. **Access Logging**: All data access logged to CloudTrail

### API Security

1. **Authentication**: JWT tokens with tenant context
2. **Authorization**: Role-based access control (RBAC)
3. **Rate Limiting**: Per-tenant rate limits
4. **Input Validation**: Strict schema validation for all inputs

### Infrastructure Security

1. **Network Isolation**: VPC with private subnets
2. **Secrets Management**: AWS Secrets Manager for all credentials
3. **Vulnerability Scanning**: Regular security scans
4. **Compliance**: SOC 2 Type II compliance

## Conclusion

This multi-tenant architecture provides:

- **Scalable API Design**: OpenAPI 3.1 with tenant-aware extensions
- **Strong Isolation**: Schema-based DB isolation, prefixed caching, and S3 policies
- **Automated Provisioning**: Terraform-based infrastructure as code
- **Performance Monitoring**: Comprehensive load testing with P95 latency targets
- **Security**: Defense-in-depth security model
- **Observability**: Full audit trail and performance monitoring

The system is designed to handle 500+ concurrent tenants while maintaining sub-500ms P95 latency and ensuring complete data isolation between tenants.
