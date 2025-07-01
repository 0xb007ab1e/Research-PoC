"""Create core contexts table and helper functions

Revision ID: 4fd7215c8370
Revises: 
Create Date: 2025-06-30 09:30:21.982507

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from db_models import get_core_schema_sql


# revision identifiers, used by Alembic.
revision: str = '4fd7215c8370'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Execute core schema SQL to create extensions and helper functions
    op.execute(get_core_schema_sql())
    
    # Create contexts table in public schema (will be template for tenant schemas)
    op.create_table(
        'contexts',
        sa.Column('id', sa.String(50), primary_key=True),
        sa.Column('context_data', JSONB, nullable=False),
        sa.Column('context_type', sa.String(100), nullable=False, index=True),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('tags', ARRAY(sa.Text), default=[], nullable=False),
        sa.Column('tenant_id', sa.String(100), nullable=False, index=True),
        sa.Column('user_id', sa.String(100), nullable=True, index=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.Integer, default=1, nullable=False),
    )
    
    # Create indexes
    op.create_index('idx_contexts_tenant_id', 'contexts', ['tenant_id'])
    op.create_index('idx_contexts_user_id', 'contexts', ['user_id'])
    op.create_index('idx_contexts_context_type', 'contexts', ['context_type'])
    op.create_index('idx_contexts_created_at', 'contexts', ['created_at'])
    op.create_index('idx_contexts_expires_at', 'contexts', ['expires_at'], postgresql_where=sa.text('expires_at IS NOT NULL'))
    op.create_index('idx_contexts_tags', 'contexts', ['tags'], postgresql_using='gin')
    op.create_index('idx_contexts_data', 'contexts', ['context_data'], postgresql_using='gin')
    
    # Create trigger for updating updated_at
    op.execute("""
        CREATE TRIGGER update_contexts_updated_at
            BEFORE UPDATE ON contexts
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop triggers first
    op.execute("DROP TRIGGER IF EXISTS update_contexts_updated_at ON contexts;")
    
    # Drop indexes
    op.drop_index('idx_contexts_data', 'contexts')
    op.drop_index('idx_contexts_tags', 'contexts')
    op.drop_index('idx_contexts_expires_at', 'contexts')
    op.drop_index('idx_contexts_created_at', 'contexts')
    op.drop_index('idx_contexts_context_type', 'contexts')
    op.drop_index('idx_contexts_user_id', 'contexts')
    op.drop_index('idx_contexts_tenant_id', 'contexts')
    
    # Drop table
    op.drop_table('contexts')
    
    # Drop helper functions
    op.execute("DROP FUNCTION IF EXISTS cleanup_expired_contexts(TEXT);")
    op.execute("DROP FUNCTION IF EXISTS create_tenant_schema(TEXT);")
    op.execute("DROP FUNCTION IF EXISTS update_updated_at_column();")
