#!/bin/bash
set -e

# Function to create database if it doesn't exist
create_database() {
    local database=$1
    echo "Creating database: $database"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        SELECT 'CREATE DATABASE $database'
        WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$database')\gexec
EOSQL
}

# Function to create user and grant permissions
create_user_and_permissions() {
    local database=$1
    local user="${database}_user"
    local password="${database}_password"
    
    echo "Creating user and permissions for database: $database"
    psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
        DO \$\$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$user') THEN
                CREATE ROLE $user LOGIN PASSWORD '$password';
            END IF;
        END
        \$\$;
        
        GRANT CONNECT ON DATABASE $database TO $user;
        GRANT USAGE ON SCHEMA public TO $user;
        GRANT CREATE ON SCHEMA public TO $user;
        GRANT ALL PRIVILEGES ON DATABASE $database TO $user;
EOSQL
}

# Create individual databases for each service
create_database "context_service"
create_database "text_summarization" 
create_database "auth_service"

# Create users and permissions for each service
create_user_and_permissions "context_service"
create_user_and_permissions "text_summarization"
create_user_and_permissions "auth_service"

echo "Database initialization completed successfully!"
