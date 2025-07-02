-- Context Service Database Schema
-- This file contains the database schema for the MCP Context Service
-- Each tenant will have its own schema (tenant_<tenant_id>)

-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create the contexts table (this will be created in each tenant schema)
CREATE TABLE IF NOT EXISTS contexts (
    id VARCHAR(50) PRIMARY KEY,  -- Format: ctx_<uuid>
    context_data JSONB NOT NULL,  -- The actual context data
    context_type VARCHAR(100) NOT NULL,  -- Type/category of context
    title VARCHAR(255),  -- Optional human-readable title
    description TEXT,  -- Optional description
    tags TEXT[] DEFAULT '{}',  -- Array of tags for categorization
    tenant_id VARCHAR(100) NOT NULL,  -- Tenant identifier
    user_id VARCHAR(100),  -- User who created/owns the context
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,  -- Optional expiration
    version INTEGER DEFAULT 1  -- For optimistic locking
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_contexts_tenant_id ON contexts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_contexts_user_id ON contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_contexts_context_type ON contexts(context_type);
CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON contexts(created_at);
CREATE INDEX IF NOT EXISTS idx_contexts_expires_at ON contexts(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contexts_tags ON contexts USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_contexts_data ON contexts USING GIN(context_data);

-- Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_contexts_updated_at
    BEFORE UPDATE ON contexts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Example of creating a tenant schema
-- This would be done programmatically for each tenant
-- CREATE SCHEMA IF NOT EXISTS tenant_example_tenant_id;
-- SET search_path TO tenant_example_tenant_id, public;
-- -- Create the table and indexes in the tenant schema
-- CREATE TABLE contexts (... same as above ...);
-- CREATE INDEX ... (same as above)

-- Function to create a new tenant schema
CREATE OR REPLACE FUNCTION create_tenant_schema(tenant_id TEXT)
RETURNS VOID AS $$
DECLARE
    schema_name TEXT;
BEGIN
    -- Validate tenant_id to prevent SQL injection
    IF tenant_id !~ '^[a-zA-Z0-9_-]+$' THEN
        RAISE EXCEPTION 'Invalid tenant ID format: %', tenant_id;
    END IF;
    
    schema_name := 'tenant_' || tenant_id;
    
    -- Create schema
    EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', schema_name);
    
    -- Set search path
    EXECUTE format('SET search_path TO %I, public', schema_name);
    
    -- Create contexts table in tenant schema
    EXECUTE format('
        CREATE TABLE IF NOT EXISTS %I.contexts (
            id VARCHAR(50) PRIMARY KEY,
            context_data JSONB NOT NULL,
            context_type VARCHAR(100) NOT NULL,
            title VARCHAR(255),
            description TEXT,
            tags TEXT[] DEFAULT ''{}''::TEXT[],
            tenant_id VARCHAR(100) NOT NULL,
            user_id VARCHAR(100),
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITH TIME ZONE,
            version INTEGER DEFAULT 1
        )', schema_name);
    
    -- Create indexes
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_tenant_id ON %I.contexts(tenant_id)', schema_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_user_id ON %I.contexts(user_id)', schema_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_context_type ON %I.contexts(context_type)', schema_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON %I.contexts(created_at)', schema_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_expires_at ON %I.contexts(expires_at) WHERE expires_at IS NOT NULL', schema_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_tags ON %I.contexts USING GIN(tags)', schema_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS idx_contexts_data ON %I.contexts USING GIN(context_data)', schema_name);
    
    -- Create trigger
    EXECUTE format('
        CREATE TRIGGER update_contexts_updated_at
            BEFORE UPDATE ON %I.contexts
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column()', schema_name);
    
    RAISE NOTICE 'Created tenant schema: %', schema_name;
END;
$$ LANGUAGE plpgsql;

-- Function to cleanup expired contexts for a tenant
CREATE OR REPLACE FUNCTION cleanup_expired_contexts(tenant_id TEXT)
RETURNS INTEGER AS $$
DECLARE
    schema_name TEXT;
    deleted_count INTEGER;
BEGIN
    -- Validate tenant_id
    IF tenant_id !~ '^[a-zA-Z0-9_-]+$' THEN
        RAISE EXCEPTION 'Invalid tenant ID format: %', tenant_id;
    END IF;
    
    schema_name := 'tenant_' || tenant_id;
    
    -- Delete expired contexts
    EXECUTE format('
        DELETE FROM %I.contexts 
        WHERE expires_at IS NOT NULL AND expires_at <= NOW()
    ', schema_name);
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Example usage:
-- SELECT create_tenant_schema('example_tenant');
-- SELECT cleanup_expired_contexts('example_tenant');
