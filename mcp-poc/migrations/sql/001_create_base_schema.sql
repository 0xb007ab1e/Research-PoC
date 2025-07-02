-- 001_create_base_schema.sql
-- Initial base schema migration for MCP multi-tenant system
-- Creates public schema tables: tenants, users, audit_logs

-- Enable UUID extension if not already enabled
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create tenants table
CREATE TABLE IF NOT EXISTS public.tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    settings JSONB DEFAULT '{}',
    max_contexts INTEGER DEFAULT 10000,
    max_storage_mb INTEGER DEFAULT 1000,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    subscription_tier VARCHAR(50) DEFAULT 'basic',
    subscription_expires_at TIMESTAMP WITH TIME ZONE,
    
    CONSTRAINT check_max_contexts_positive CHECK (max_contexts > 0),
    CONSTRAINT check_max_storage_positive CHECK (max_storage_mb > 0),
    CONSTRAINT check_slug_format CHECK (slug ~ '^[a-z0-9-]+$')
);

-- Create indexes for tenants table
CREATE INDEX IF NOT EXISTS idx_tenant_slug ON public.tenants(slug);
CREATE INDEX IF NOT EXISTS idx_tenant_active ON public.tenants(is_active);

-- Create users table
CREATE TABLE IF NOT EXISTS public.users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    email VARCHAR(255) NOT NULL,
    external_id VARCHAR(255),
    username VARCHAR(100),
    full_name VARCHAR(255),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_admin BOOLEAN NOT NULL DEFAULT false,
    last_login_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    preferences JSONB DEFAULT '{}',
    timezone VARCHAR(50) DEFAULT 'UTC',
    language VARCHAR(10) DEFAULT 'en',
    
    CONSTRAINT uq_tenant_user_email UNIQUE (tenant_id, email),
    CONSTRAINT uq_tenant_user_username UNIQUE (tenant_id, username)
);

-- Create indexes for users table
CREATE INDEX IF NOT EXISTS idx_user_tenant_email ON public.users(tenant_id, email);
CREATE INDEX IF NOT EXISTS idx_user_external_id ON public.users(external_id);
CREATE INDEX IF NOT EXISTS idx_user_active ON public.users(is_active);
CREATE INDEX IF NOT EXISTS ix_users_email ON public.users(email);

-- Create audit_logs table
CREATE TABLE IF NOT EXISTS public.audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES public.tenants(id) ON DELETE CASCADE,
    user_id UUID REFERENCES public.users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    request_id UUID,
    ip_address VARCHAR(45),
    user_agent TEXT,
    details JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    status VARCHAR(20) DEFAULT 'success',
    error_message TEXT,
    
    CONSTRAINT check_audit_status CHECK (status IN ('success', 'failure', 'error'))
);

-- Create indexes for audit_logs table
CREATE INDEX IF NOT EXISTS idx_audit_tenant_timestamp ON public.audit_logs(tenant_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_user_timestamp ON public.audit_logs(user_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_action ON public.audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON public.audit_logs(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_request_id ON public.audit_logs(request_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at columns
CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON public.tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
