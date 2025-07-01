"""
SQLAlchemy database models for the MCP Context Service
Defines database tables and relationships for context storage
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, ARRAY
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()


class Context(Base):
    """Context table model for storing context data in tenant schemas"""
    
    __tablename__ = "contexts"
    
    # Primary key with custom format: ctx_<uuid>
    id = Column(String(50), primary_key=True)
    
    # Core context data stored as JSONB
    context_data = Column(JSONB, nullable=False)
    
    # Context metadata
    context_type = Column(String(100), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    tags = Column(ARRAY(Text), default=[], nullable=False, index=True)
    
    # Tenant and user information
    tenant_id = Column(String(100), nullable=False, index=True)
    user_id = Column(String(100), nullable=True, index=True)
    
    # Timestamps
    created_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(),
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True), 
        nullable=False, 
        default=func.now(),
        onupdate=func.now()
    )
    expires_at = Column(
        DateTime(timezone=True), 
        nullable=True,
        index=True
    )
    
    # Version for optimistic locking
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<Context(id='{self.id}', type='{self.context_type}', tenant='{self.tenant_id}')>"


# Function to create database schema with helper functions
def get_core_schema_sql():
    """
    Returns the SQL for creating core database functions and extensions
    that are not tied to specific tenant schemas
    """
    return """
-- Create extension for UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

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
"""


def get_tenant_indexes_sql(schema_name: str):
    """
    Returns SQL for creating indexes on the contexts table in a tenant schema
    """
    return f"""
-- Create indexes for performance in {schema_name}
CREATE INDEX IF NOT EXISTS idx_contexts_tenant_id ON {schema_name}.contexts(tenant_id);
CREATE INDEX IF NOT EXISTS idx_contexts_user_id ON {schema_name}.contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_contexts_context_type ON {schema_name}.contexts(context_type);
CREATE INDEX IF NOT EXISTS idx_contexts_created_at ON {schema_name}.contexts(created_at);
CREATE INDEX IF NOT EXISTS idx_contexts_expires_at ON {schema_name}.contexts(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_contexts_tags ON {schema_name}.contexts USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_contexts_data ON {schema_name}.contexts USING GIN(context_data);

-- Create trigger to update updated_at timestamp
CREATE TRIGGER update_contexts_updated_at
    BEFORE UPDATE ON {schema_name}.contexts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
"""
