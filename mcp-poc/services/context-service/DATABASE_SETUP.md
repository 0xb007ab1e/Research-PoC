# Context Service Database Setup

This document describes the database setup and migration process for the MCP Context Service.

## Overview

The Context Service uses a multi-tenant PostgreSQL database architecture where:
- Core database functions and extensions are created in the `public` schema
- Each tenant gets its own schema (`tenant_<tenant_id>`)
- The `contexts` table is created in each tenant schema with appropriate indexes and triggers

## Database Bootstrap Process

### 1. Alembic Migrations

The service uses Alembic for database migrations:

```bash
# Initialize Alembic (already done)
alembic init migrations

# Create a new migration
alembic revision -m "Description of changes"

# Run migrations
alembic upgrade head
```

### 2. Database Bootstrap Script

The `scripts/db-bootstrap.py` script handles:
- Creating core database functions and extensions
- Running Alembic migrations on the public schema
- Creating tenant schemas and tables
- Setting up indexes and triggers for each tenant

#### Usage

```bash
# Bootstrap with health check first
python scripts/db-bootstrap.py --health-check || python scripts/db-bootstrap.py

# Bootstrap specific tenant
python scripts/db-bootstrap.py --tenant-id my-tenant

# Bootstrap multiple tenants
python scripts/db-bootstrap.py --tenant-ids "tenant1,tenant2,tenant3"

# Force recreate existing schemas
python scripts/db-bootstrap.py --force-recreate

# Health check only
python scripts/db-bootstrap.py --health-check
```

#### Environment Variables

The bootstrap script uses the following environment variables:

- `DB_HOST` - PostgreSQL host (default: localhost)
- `DB_PORT` - PostgreSQL port (default: 5432)
- `DB_NAME` - Database name (default: context_service)
- `DB_USER` - Database user (default: context_user)
- `DB_PASSWORD` - Database password
- `TENANT_IDS` - Comma-separated list of tenant IDs to bootstrap

## Local Development Setup

For local development, the Makefile includes automatic database bootstrapping:

```bash
# This will run the bootstrap script before starting the service
make local-run
```

The bootstrap process:
1. Checks if the database is already set up (health check)
2. If not, runs the full bootstrap process
3. Creates default tenant if no tenant IDs are specified
4. Starts the service

## Kubernetes/Helm Deployment

When deploying with Helm, the database bootstrap is handled automatically:

### Post-Install Hook

The Helm chart includes a post-install job that runs the bootstrap script:

```yaml
# In values.yaml
bootstrap:
  enabled: true
  image:
    repository: context-service
    tag: "latest"
  restartPolicy: OnFailure
  backoffLimit: 3

database:
  tenantIds: "default,demo"
```

The post-install job:
1. Runs after the main deployment
2. Executes the bootstrap script with configured tenant IDs
3. Ensures the database is ready before the service starts handling requests

### Deployment Process

```bash
# Deploy with Helm
helm install context-service ./helm/context-service

# Upgrade with automatic bootstrap
helm upgrade context-service ./helm/context-service
```

## Database Schema Structure

### Core Functions (Public Schema)

- `create_tenant_schema(tenant_id)` - Creates a new tenant schema with contexts table
- `cleanup_expired_contexts(tenant_id)` - Removes expired contexts for a tenant
- `update_updated_at_column()` - Trigger function to update timestamps

### Tenant Schema Structure

Each tenant schema contains:

#### Contexts Table
```sql
CREATE TABLE contexts (
    id VARCHAR(50) PRIMARY KEY,              -- Format: ctx_<uuid>
    context_data JSONB NOT NULL,             -- The actual context data
    context_type VARCHAR(100) NOT NULL,      -- Type/category of context
    title VARCHAR(255),                      -- Optional human-readable title
    description TEXT,                        -- Optional description
    tags TEXT[] DEFAULT '{}',                -- Array of tags for categorization
    tenant_id VARCHAR(100) NOT NULL,         -- Tenant identifier
    user_id VARCHAR(100),                    -- User who created/owns the context
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,    -- Optional expiration
    version INTEGER DEFAULT 1               -- For optimistic locking
);
```

#### Indexes
- `idx_contexts_tenant_id` - Fast tenant-based queries
- `idx_contexts_user_id` - User-specific context lookup
- `idx_contexts_context_type` - Type-based filtering
- `idx_contexts_created_at` - Time-based queries
- `idx_contexts_expires_at` - Expiration cleanup (partial index)
- `idx_contexts_tags` - GIN index for tag array searches
- `idx_contexts_data` - GIN index for JSONB content searches

#### Triggers
- `update_contexts_updated_at` - Automatically updates `updated_at` timestamp

## Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure PostgreSQL is running
   - Check connection parameters (host, port, credentials)

2. **Permission Denied**
   - Verify database user has CREATE privileges
   - Check schema creation permissions

3. **Migration Conflicts**
   - Use `alembic current` to check current revision
   - Use `alembic history` to see migration history
   - Resolve conflicts manually if needed

### Database Verification

```bash
# Check if core functions exist
psql -h localhost -U context_user -d context_service -c "
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
AND routine_name IN ('create_tenant_schema', 'cleanup_expired_contexts');
"

# Check tenant schemas
psql -h localhost -U context_user -d context_service -c "
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name LIKE 'tenant_%';
"

# Check contexts table in a tenant schema
psql -h localhost -U context_user -d context_service -c "
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'tenant_default' 
AND table_name = 'contexts';
"
```

## Best Practices

1. **Backup Before Migrations**
   - Always backup the database before running migrations in production

2. **Test Migrations**
   - Test all migrations in a staging environment first

3. **Monitor Bootstrap Jobs**
   - Check Kubernetes job logs for bootstrap failures
   - Set up alerts for failed bootstrap jobs

4. **Tenant Isolation**
   - Each tenant's data is isolated in its own schema
   - Cross-tenant queries require explicit schema specification

5. **Performance Considerations**
   - Monitor GIN index usage for JSONB queries
   - Consider partitioning for high-volume tenants
   - Implement regular cleanup of expired contexts
