#!/bin/bash

# Example script showing how the application can source database credentials
# This would typically be used in the application's entrypoint script

# Source the database credentials from Vault Agent
if [ -f "/vault/secrets/db-credentials" ]; then
    echo "Loading database credentials from Vault..."
    source /vault/secrets/db-credentials
    
    # Verify credentials are loaded
    if [ -n "$DB_USERNAME" ] && [ -n "$DB_PASSWORD" ]; then
        echo "Database credentials loaded successfully"
        echo "Username: $DB_USERNAME"
        echo "Password: [REDACTED]"
    else
        echo "ERROR: Failed to load database credentials"
        exit 1
    fi
else
    echo "ERROR: Vault credentials file not found at /vault/secrets/db-credentials"
    exit 1
fi

# Example: Use credentials to connect to database
# export DATABASE_URL="postgresql://$DB_USERNAME:$DB_PASSWORD@postgres:5432/mydb"

# Start the main application
# exec "$@"
