# Vault Dynamic Database Credentials Setup

This directory contains scripts and configuration for setting up Vault dynamic database credentials for the text-summarization service.

## Files

- `vault-db-setup.sh` - Main setup script that configures Vault
- `vault-policy.hcl` - Vault policy file defining permissions for the application
- `vault-setup-README.md` - This documentation file

## Prerequisites

1. Vault server must be running and accessible
2. You must be authenticated to Vault with sufficient permissions
3. Kubernetes auth method must be enabled in Vault
4. PostgreSQL database must be accessible from Vault

## Setup Steps

### 1. Configure Database Connection

Before running the setup script, update the database connection URL in `vault-db-setup.sh`:

```bash
# Update this line with your actual database connection details
connection_url=postgresql://{{username}}:{{password}}@db.example.com:5432/mydb?sslmode=disable
```

Replace:
- `db.example.com` with your database hostname
- `5432` with your database port (if different)
- `mydb` with your database name

### 2. Run the Setup Script

```bash
./scripts/vault-db-setup.sh
```

This script will:
- Enable the database secrets engine
- Configure the PostgreSQL database plugin
- Create `readonly` and `readwrite` database roles
- Create a Vault policy for the application
- Configure Kubernetes authentication role

### 3. Deploy the Application

The Helm chart is now configured to use Vault Agent sidecar. Deploy with:

```bash
helm upgrade --install text-summarization ./helm/text-summarization \
  --set vault.enabled=true
```

## How It Works

1. **Vault Agent Sidecar**: The deployment includes Vault Agent annotations that inject a sidecar container
2. **Authentication**: The pod authenticates to Vault using the Kubernetes service account
3. **Dynamic Credentials**: Vault Agent fetches database credentials and writes them to `/vault/secrets/db-credentials`
4. **Environment Variables**: The credentials are templated as environment variables that the application can source

## Database Roles

### readonly
- Permissions: SELECT on all tables in public schema
- Default TTL: 1 hour
- Max TTL: 24 hours

### readwrite
- Permissions: SELECT, INSERT, UPDATE, DELETE on all tables in public schema
- Default TTL: 1 hour
- Max TTL: 24 hours

## Security Features

- Credentials are dynamically generated for each request
- Credentials have limited TTL and are automatically rotated
- Access is controlled via Kubernetes service account binding
- Vault policy restricts access to only necessary paths

## Troubleshooting

### Check Vault Agent Status
```bash
kubectl logs <pod-name> -c vault-agent
```

### Verify Credentials
```bash
kubectl exec <pod-name> -- cat /vault/secrets/db-credentials
```

### Check Vault Configuration
```bash
vault read database/config/my-postgresql-database
vault read database/roles/readwrite
vault read auth/kubernetes/role/my-app
```

## Customization

To use different database roles or configurations:

1. Update the role name in `values.yaml` under `vault.agent.templates`
2. Ensure the corresponding role exists in Vault
3. Update the Vault policy if needed to allow access to the new role
