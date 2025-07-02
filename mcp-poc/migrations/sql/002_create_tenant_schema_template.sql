-- 002_create_tenant_schema_template.sql
-- Template for creating tenant-specific schemas
-- Creates contexts and summaries tables for a specific tenant
-- This script should be run with the tenant schema name substituted

-- Replace {{TENANT_SCHEMA}} with the actual tenant schema name when running this script
-- Example: tenant_acme, tenant_example, etc.

-- Create tenant schema if it doesn't exist
-- CREATE SCHEMA IF NOT EXISTS {{TENANT_SCHEMA}};

-- Create contexts table in tenant schema
CREATE TABLE IF NOT EXISTS {{TENANT_SCHEMA}}.contexts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL, -- References public.users.id
    context_data JSONB NOT NULL,
    context_type VARCHAR(100) NOT NULL,
    title VARCHAR(255),
    description TEXT,
    tags JSONB DEFAULT '[]',
    source_system VARCHAR(100),
    source_reference VARCHAR(255),
    priority INTEGER DEFAULT 0,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    accessed_at TIMESTAMP WITH TIME ZONE,
    access_count INTEGER DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_archived BOOLEAN NOT NULL DEFAULT false,
    
    CONSTRAINT check_context_priority_positive CHECK (priority >= 0),
    CONSTRAINT check_context_access_count_positive CHECK (access_count >= 0),
    CONSTRAINT check_context_version_positive CHECK (version > 0)
);

-- Create indexes for contexts table
CREATE INDEX IF NOT EXISTS idx_context_user_id ON {{TENANT_SCHEMA}}.contexts(user_id);
CREATE INDEX IF NOT EXISTS idx_context_type ON {{TENANT_SCHEMA}}.contexts(context_type);
CREATE INDEX IF NOT EXISTS idx_context_created_at ON {{TENANT_SCHEMA}}.contexts(created_at);
CREATE INDEX IF NOT EXISTS idx_context_tags ON {{TENANT_SCHEMA}}.contexts USING gin(tags);
CREATE INDEX IF NOT EXISTS idx_context_active ON {{TENANT_SCHEMA}}.contexts(is_active);
CREATE INDEX IF NOT EXISTS idx_context_expires_at ON {{TENANT_SCHEMA}}.contexts(expires_at);

-- Create summaries table in tenant schema
CREATE TABLE IF NOT EXISTS {{TENANT_SCHEMA}}.summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    context_id UUID NOT NULL REFERENCES {{TENANT_SCHEMA}}.contexts(id) ON DELETE CASCADE,
    user_id UUID NOT NULL, -- References public.users.id
    original_text TEXT NOT NULL,
    summarized_text TEXT NOT NULL,
    ai_model VARCHAR(100) NOT NULL,
    semantic_score VARCHAR(10),
    processing_time_ms INTEGER,
    original_length INTEGER NOT NULL,
    summary_length INTEGER NOT NULL,
    compression_ratio VARCHAR(10),
    quality_metrics JSONB DEFAULT '{}',
    request_id UUID,
    retry_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'completed',
    error_message TEXT,
    warnings JSONB DEFAULT '[]',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    access_count INTEGER DEFAULT 0,
    last_accessed_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT check_summary_original_length_positive CHECK (original_length > 0),
    CONSTRAINT check_summary_length_positive CHECK (summary_length > 0),
    CONSTRAINT check_summary_retry_count_positive CHECK (retry_count >= 0),
    CONSTRAINT check_summary_access_count_positive CHECK (access_count >= 0),
    CONSTRAINT check_summary_status CHECK (status IN ('pending', 'completed', 'failed'))
);

-- Create indexes for summaries table
CREATE INDEX IF NOT EXISTS idx_summary_context_id ON {{TENANT_SCHEMA}}.summaries(context_id);
CREATE INDEX IF NOT EXISTS idx_summary_user_id ON {{TENANT_SCHEMA}}.summaries(user_id);
CREATE INDEX IF NOT EXISTS idx_summary_created_at ON {{TENANT_SCHEMA}}.summaries(created_at);
CREATE INDEX IF NOT EXISTS idx_summary_status ON {{TENANT_SCHEMA}}.summaries(status);
CREATE INDEX IF NOT EXISTS idx_summary_ai_model ON {{TENANT_SCHEMA}}.summaries(ai_model);
CREATE INDEX IF NOT EXISTS idx_summary_request_id ON {{TENANT_SCHEMA}}.summaries(request_id);

-- Create triggers for updated_at columns in tenant schema
CREATE TRIGGER update_contexts_updated_at BEFORE UPDATE ON {{TENANT_SCHEMA}}.contexts
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();

CREATE TRIGGER update_summaries_updated_at BEFORE UPDATE ON {{TENANT_SCHEMA}}.summaries
    FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();
