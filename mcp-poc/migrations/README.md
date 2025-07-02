# MCP Database Migrations

This directory contains database migration tooling for the MCP (Model Context Protocol) multi-tenant system.

## Overview

The MCP system uses a multi-tenant database architecture with:
- **Public schema**: Contains base tables (`tenants`, `users`, `audit_logs`)
- **Tenant-specific schemas**: Each tenant gets their own schema containing `contexts` and `summaries` tables

## Directory Structure

```
migrations/
├── alembic/                    # Alembic migration framework
│   ├── env.py                 # Alembic environment configuration
│   ├── script.py.mako         # Migration template
│   └── versions/              # Migration versions
│       ├── 001_*.py          # Base schema migration
│       └── 002_*.py          # Tenant schema template
├── sql/                       # Raw SQL scripts (for Go services)
│   ├── 001_create_base_schema.sql
│   └── 002_create_tenant_schema_template.sql
├── go/                        # Go migration utilities
│   └── migrate.go            # Go migration runner
├── database_models.py         # SQLAlchemy models
├── init_db.py                # Tenant initialization script
├── alembic.ini               # Alembic configuration
└── README.md                 # This file
```

## Requirements

### Python Services
- Python 3.11+
- Alembic 1.13.1+
- SQLAlchemy 2.0.23+
- psycopg2-binary 2.9.9+

### Go Services
- Go 1.21+
- github.com/lib/pq driver

## Usage

### Setting up Alembic

1. Install dependencies:
```bash
cd migrations
pip install alembic sqlalchemy psycopg2-binary
```

2. Set database URL:
```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/mcp_db"
```

### Running Migrations

#### Base Schema (Public Tables)

Using Alembic (Python):
```bash
cd migrations
alembic upgrade head
```

Using Go migration utility:
```bash
cd migrations/go
go build -o migrate migrate.go
./migrate -type=base
```

#### Tenant-Specific Schema

Using Alembic (Python):
```bash
cd migrations
export TENANT_ID=your-tenant-id
alembic upgrade head
```

Using Go migration utility:
```bash
cd migrations/go
./migrate -type=tenant -tenant-schema=tenant_your_tenant_slug
```

### Creating New Tenants

Use the tenant initialization script:
```bash
cd migrations
python init_db.py --tenant-slug=new-tenant
```

This script will:
1. Create a new tenant record in the `tenants` table
2. Create the tenant-specific schema
3. Run migrations for the tenant schema

### Migration Management

#### Creating New Migrations

```bash
cd migrations
alembic revision --autogenerate -m "Description of changes"
```

#### Checking Migration Status

```bash
alembic current
alembic history
```

#### Rolling Back Migrations

```bash
alembic downgrade -1      # Rollback one migration
alembic downgrade 001     # Rollback to specific revision
```

## Database Schema

### Public Schema Tables

#### `tenants`
- Stores tenant information and configuration
- Each tenant gets a unique slug used for schema naming
- Contains subscription and billing information

#### `users`
- Multi-tenant user table
- Users belong to a specific tenant
- Supports OAuth/SSO integration

#### `audit_logs`
- System-wide audit logging
- Tracks all significant actions across tenants
- Includes request tracing and security events

### Tenant Schema Tables (per tenant)

#### `contexts`
- Stores contextual data for the tenant
- Supports tags, expiration, and versioning
- Includes usage tracking and archival

#### `summaries`
- AI-generated text summaries
- Links to contexts and tracks quality metrics
- Stores processing metadata and retry information

## Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
- `TENANT_ID`: For tenant-specific migrations (Alembic)

## CI/CD Integration

The system includes GitHub Actions workflows:

1. **Migration Validation**: Tests all migration scripts
2. **Tenant Bootstrap Testing**: Validates tenant creation process
3. **Rollback Testing**: Ensures migrations can be safely rolled back
4. **Deployment**: Applies migrations to target environments

### Running in CI

The workflow automatically runs `alembic upgrade head` during the test phase to ensure migrations work correctly.

## Multi-Language Support

### Python Services
Use Alembic for full-featured migration management with automatic schema detection and rollback support.

### Go Services
Use the provided Go utility (`migrate.go`) for simple migration execution. SQL scripts support template substitution for tenant schemas.

## Best Practices

1. **Always test migrations** on a copy of production data
2. **Use transactions** for complex migrations
3. **Backup before deployment** in production environments
4. **Monitor migration performance** for large datasets
5. **Keep migrations reversible** when possible
6. **Document breaking changes** in migration comments

## Troubleshooting

### Common Issues

1. **Connection refused**: Check DATABASE_URL and database server status
2. **Permission denied**: Ensure database user has CREATE/DROP privileges
3. **Migration conflicts**: Use `alembic merge` to resolve conflicting revisions
4. **Schema not found**: Verify tenant schema creation completed successfully

### Debug Commands

```bash
# Check Alembic configuration
alembic check

# Verify database connection
alembic current

# Show migration history
alembic history --verbose

# Show SQL without executing
alembic upgrade head --sql
```

## Security Considerations

- Migration scripts have full database access
- Use environment variables for sensitive configuration
- Audit migration execution in production
- Validate tenant isolation after schema creation
- Monitor for SQL injection in dynamic schema creation

## Performance Notes

- Index creation can be slow on large tables
- Consider online schema changes for production
- Monitor long-running migrations
- Use batched operations for large data updates
- Test migration performance on production-sized datasets
