"""
SQLAlchemy database models for MCP multi-tenant system.

This module defines:
- Base (public schema): tenants, users, audit_logs
- TenantBase (per-tenant schema): contexts, summaries
"""

from datetime import datetime
from typing import Optional, Dict, Any
import uuid

from sqlalchemy import (
    Column, String, DateTime, Text, Boolean, Integer, 
    ForeignKey, JSON, Index, UniqueConstraint, CheckConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, validates
from sqlalchemy.sql import func

# Base for public schema tables
Base = declarative_base()

# Base for tenant-specific schema tables  
TenantBase = declarative_base()


class Tenant(Base):
    """
    Tenant model - stores in public schema.
    Each tenant gets their own schema for contexts and summaries.
    """
    __tablename__ = "tenants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text)
    
    # Configuration
    settings = Column(JSON, default=dict)
    max_contexts = Column(Integer, default=10000)
    max_storage_mb = Column(Integer, default=1000)
    
    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Billing and subscription info
    subscription_tier = Column(String(50), default="basic")
    subscription_expires_at = Column(DateTime(timezone=True))
    
    # Database schema name (computed)
    @property
    def schema_name(self) -> str:
        return f"tenant_{self.slug}"
    
    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="tenant")
    
    # Constraints
    __table_args__ = (
        CheckConstraint('max_contexts > 0', name='check_max_contexts_positive'),
        CheckConstraint('max_storage_mb > 0', name='check_max_storage_positive'),
        CheckConstraint("slug ~ '^[a-z0-9-]+$'", name='check_slug_format'),
        Index('idx_tenant_slug', 'slug'),
        Index('idx_tenant_active', 'is_active'),
    )
    
    @validates('slug')
    def validate_slug(self, key, value):
        """Validate tenant slug format."""
        if not value or not value.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Slug must contain only alphanumeric characters and hyphens")
        return value.lower()
    
    def __repr__(self):
        return f"<Tenant(id={self.id}, slug='{self.slug}', name='{self.name}')>"


class User(Base):
    """
    User model - stores in public schema.
    Users belong to tenants and can access tenant-specific data.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    
    # User identity
    email = Column(String(255), nullable=False, index=True)
    external_id = Column(String(255), index=True)  # For OAuth/SSO integration
    username = Column(String(100))
    full_name = Column(String(255))
    
    # User status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    last_login_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # User preferences and settings
    preferences = Column(JSON, default=dict)
    timezone = Column(String(50), default="UTC")
    language = Column(String(10), default="en")
    
    # Relationships
    tenant = relationship("Tenant", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uq_tenant_user_email'),
        UniqueConstraint('tenant_id', 'username', name='uq_tenant_user_username'),
        Index('idx_user_tenant_email', 'tenant_id', 'email'),
        Index('idx_user_external_id', 'external_id'),
        Index('idx_user_active', 'is_active'),
    )
    
    @validates('email')
    def validate_email(self, key, value):
        """Basic email validation."""
        if value and '@' not in value:
            raise ValueError("Invalid email format")
        return value.lower() if value else value
    
    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', tenant_id={self.tenant_id})>"


class AuditLog(Base):
    """
    Audit log model - stores in public schema.
    Tracks all significant actions across the system.
    """
    __tablename__ = "audit_logs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    
    # Action details
    action = Column(String(100), nullable=False)  # e.g., 'context.create', 'user.login'
    resource_type = Column(String(50))  # e.g., 'context', 'summary', 'user'
    resource_id = Column(String(255))   # ID of the affected resource
    
    # Request context
    request_id = Column(UUID(as_uuid=True))
    ip_address = Column(String(45))  # IPv6 compatible
    user_agent = Column(Text)
    
    # Additional data
    details = Column(JSON, default=dict)
    metadata = Column(JSON, default=dict)
    
    # Timing
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # Status
    status = Column(String(20), default="success")  # success, failure, error
    error_message = Column(Text)
    
    # Relationships
    tenant = relationship("Tenant", back_populates="audit_logs")
    user = relationship("User", back_populates="audit_logs")
    
    # Constraints
    __table_args__ = (
        Index('idx_audit_tenant_timestamp', 'tenant_id', 'timestamp'),
        Index('idx_audit_user_timestamp', 'user_id', 'timestamp'),
        Index('idx_audit_action', 'action'),
        Index('idx_audit_resource', 'resource_type', 'resource_id'),
        Index('idx_audit_request_id', 'request_id'),
        CheckConstraint("status IN ('success', 'failure', 'error')", name='check_audit_status'),
    )
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, action='{self.action}', tenant_id={self.tenant_id})>"


# Tenant-specific models (stored in per-tenant schemas)

class Context(TenantBase):
    """
    Context model - stored in tenant-specific schema.
    Stores contextual data for each tenant.
    """
    __tablename__ = "contexts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # References public.users.id
    
    # Context content
    context_data = Column(JSON, nullable=False)
    context_type = Column(String(100), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    tags = Column(JSON, default=list)  # List of strings
    
    # Metadata
    source_system = Column(String(100))
    source_reference = Column(String(255))
    priority = Column(Integer, default=0)
    
    # Lifecycle
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    accessed_at = Column(DateTime(timezone=True))
    access_count = Column(Integer, default=0)
    
    # Versioning for optimistic locking
    version = Column(Integer, default=1, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    summaries = relationship("Summary", back_populates="context", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        Index('idx_context_user_id', 'user_id'),
        Index('idx_context_type', 'context_type'),
        Index('idx_context_created_at', 'created_at'),
        Index('idx_context_tags', 'tags', postgresql_using='gin'),
        Index('idx_context_active', 'is_active'),
        Index('idx_context_expires_at', 'expires_at'),
        CheckConstraint('priority >= 0', name='check_context_priority_positive'),
        CheckConstraint('access_count >= 0', name='check_context_access_count_positive'),
        CheckConstraint('version > 0', name='check_context_version_positive'),
    )
    
    @validates('context_type')
    def validate_context_type(self, key, value):
        """Validate context type format."""
        if not value or not all(c.isalnum() or c in '-_.' for c in value):
            raise ValueError("Context type can only contain alphanumeric characters, hyphens, underscores, and dots")
        return value
    
    def __repr__(self):
        return f"<Context(id={self.id}, type='{self.context_type}', user_id={self.user_id})>"


class Summary(TenantBase):
    """
    Summary model - stored in tenant-specific schema.
    Stores text summaries generated by the AI service.
    """
    __tablename__ = "summaries"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    context_id = Column(UUID(as_uuid=True), ForeignKey("contexts.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(UUID(as_uuid=True), nullable=False)  # References public.users.id
    
    # Content
    original_text = Column(Text, nullable=False)
    summarized_text = Column(Text, nullable=False)
    
    # Processing metadata
    ai_model = Column(String(100), nullable=False)
    semantic_score = Column(String(10))  # Store as string to avoid float precision issues
    processing_time_ms = Column(Integer)
    
    # Quality metrics
    original_length = Column(Integer, nullable=False)
    summary_length = Column(Integer, nullable=False)
    compression_ratio = Column(String(10))  # Store as string
    quality_metrics = Column(JSON, default=dict)
    
    # Request context
    request_id = Column(UUID(as_uuid=True))
    retry_count = Column(Integer, default=0)
    
    # Status and lifecycle
    status = Column(String(20), default="completed")  # pending, completed, failed
    error_message = Column(Text)
    warnings = Column(JSON, default=list)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Usage tracking
    access_count = Column(Integer, default=0)
    last_accessed_at = Column(DateTime(timezone=True))
    
    # Relationships
    context = relationship("Context", back_populates="summaries")
    
    # Constraints
    __table_args__ = (
        Index('idx_summary_context_id', 'context_id'),
        Index('idx_summary_user_id', 'user_id'),
        Index('idx_summary_created_at', 'created_at'),
        Index('idx_summary_status', 'status'),
        Index('idx_summary_ai_model', 'ai_model'),
        Index('idx_summary_request_id', 'request_id'),
        CheckConstraint('original_length > 0', name='check_summary_original_length_positive'),
        CheckConstraint('summary_length > 0', name='check_summary_length_positive'),
        CheckConstraint('retry_count >= 0', name='check_summary_retry_count_positive'),
        CheckConstraint('access_count >= 0', name='check_summary_access_count_positive'),
        CheckConstraint("status IN ('pending', 'completed', 'failed')", name='check_summary_status'),
    )
    
    @validates('ai_model')
    def validate_ai_model(self, key, value):
        """Validate AI model name."""
        if not value:
            raise ValueError("AI model is required")
        return value.lower()
    
    def __repr__(self):
        return f"<Summary(id={self.id}, context_id={self.context_id}, model='{self.ai_model}')>"


# Helper function to create database metadata
def get_all_metadata():
    """Get all metadata for both public and tenant schemas."""
    return {
        'public': Base.metadata,
        'tenant': TenantBase.metadata
    }
