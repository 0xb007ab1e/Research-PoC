"""Tenant schema template migration

Revision ID: 002
Revises: 001
Create Date: 2024-12-14 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    This migration defines the template for tenant-specific schemas.
    It should be run with TENANT_ID environment variable set.
    """
    # Create contexts table in tenant schema
    op.create_table('contexts',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('context_data', sa.JSON(), nullable=False),
    sa.Column('context_type', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=True),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('tags', sa.JSON(), nullable=True),
    sa.Column('source_system', sa.String(length=100), nullable=True),
    sa.Column('source_reference', sa.String(length=255), nullable=True),
    sa.Column('priority', sa.Integer(), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('accessed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('access_count', sa.Integer(), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('is_archived', sa.Boolean(), nullable=False),
    sa.CheckConstraint('access_count >= 0', name='check_context_access_count_positive'),
    sa.CheckConstraint('priority >= 0', name='check_context_priority_positive'),
    sa.CheckConstraint('version > 0', name='check_context_version_positive'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_context_active', 'contexts', ['is_active'], unique=False)
    op.create_index('idx_context_created_at', 'contexts', ['created_at'], unique=False)
    op.create_index('idx_context_expires_at', 'contexts', ['expires_at'], unique=False)
    op.create_index('idx_context_tags', 'contexts', ['tags'], unique=False, postgresql_using='gin')
    op.create_index('idx_context_type', 'contexts', ['context_type'], unique=False)
    op.create_index('idx_context_user_id', 'contexts', ['user_id'], unique=False)

    # Create summaries table in tenant schema
    op.create_table('summaries',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('context_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('original_text', sa.Text(), nullable=False),
    sa.Column('summarized_text', sa.Text(), nullable=False),
    sa.Column('ai_model', sa.String(length=100), nullable=False),
    sa.Column('semantic_score', sa.String(length=10), nullable=True),
    sa.Column('processing_time_ms', sa.Integer(), nullable=True),
    sa.Column('original_length', sa.Integer(), nullable=False),
    sa.Column('summary_length', sa.Integer(), nullable=False),
    sa.Column('compression_ratio', sa.String(length=10), nullable=True),
    sa.Column('quality_metrics', sa.JSON(), nullable=True),
    sa.Column('request_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('retry_count', sa.Integer(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('warnings', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('access_count', sa.Integer(), nullable=True),
    sa.Column('last_accessed_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint('access_count >= 0', name='check_summary_access_count_positive'),
    sa.CheckConstraint('original_length > 0', name='check_summary_original_length_positive'),
    sa.CheckConstraint('retry_count >= 0', name='check_summary_retry_count_positive'),
    sa.CheckConstraint("status IN ('pending', 'completed', 'failed')", name='check_summary_status'),
    sa.CheckConstraint('summary_length > 0', name='check_summary_length_positive'),
    sa.ForeignKeyConstraint(['context_id'], ['contexts.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_summary_ai_model', 'summaries', ['ai_model'], unique=False)
    op.create_index('idx_summary_context_id', 'summaries', ['context_id'], unique=False)
    op.create_index('idx_summary_created_at', 'summaries', ['created_at'], unique=False)
    op.create_index('idx_summary_request_id', 'summaries', ['request_id'], unique=False)
    op.create_index('idx_summary_status', 'summaries', ['status'], unique=False)
    op.create_index('idx_summary_user_id', 'summaries', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_summary_user_id', table_name='summaries')
    op.drop_index('idx_summary_status', table_name='summaries')
    op.drop_index('idx_summary_request_id', table_name='summaries')
    op.drop_index('idx_summary_created_at', table_name='summaries')
    op.drop_index('idx_summary_context_id', table_name='summaries')
    op.drop_index('idx_summary_ai_model', table_name='summaries')
    op.drop_table('summaries')
    op.drop_index('idx_context_user_id', table_name='contexts')
    op.drop_index('idx_context_type', table_name='contexts')
    op.drop_index('idx_context_tags', table_name='contexts')
    op.drop_index('idx_context_expires_at', table_name='contexts')
    op.drop_index('idx_context_created_at', table_name='contexts')
    op.drop_index('idx_context_active', table_name='contexts')
    op.drop_table('contexts')
