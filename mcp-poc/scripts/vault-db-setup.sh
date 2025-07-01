#!/bin/bash

set -e

# Enable the database secrets engine
vault secrets enable database

# Configure the PostgreSQL database plugin
vault write database/config/my-postgresql-database \
    plugin_name=postgresql-database-plugin \
    allowed_roles="readonly, readwrite" \
    connection_url=postgresql://{{username}}:{{password}}@db.example.com:5432/mydb?sslmode=disable

# Create a read-only role
vault write database/roles/readonly \
    db_name=my-postgresql-database \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '\"{{password}}\' VALID UNTIL \"{{expiration}}\'; GRANT SELECT ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"

# Create a read-write role
vault write database/roles/readwrite \
    db_name=my-postgresql-database \
    creation_statements="CREATE ROLE \"{{name}}\" WITH LOGIN PASSWORD '\"{{password}}\' VALID UNTIL \"{{expiration}}\'; GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO \"{{name}}\";" \
    default_ttl="1h" \
    max_ttl="24h"

# Create a policy for the application
vault policy write my-app-policy scripts/vault-policy.hcl

# Create a Kubernetes auth role for the application
vault write auth/kubernetes/role/my-app \
    bound_service_account_names=text-summarization-service \
    bound_service_account_namespaces=default \
    policies=my-app-policy \
    ttl=24h

