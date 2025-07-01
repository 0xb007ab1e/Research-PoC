"""
Alembic environment configuration for MCP multi-tenant database setup.
Handles both public schema (base tables) and per-tenant schemas.
"""

import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context

# Add the parent directory to the path so we can import models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from database_models import Base, TenantBase

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Base metadata for autogenerate support
# Include both public and tenant-specific models
target_metadata = [Base.metadata, TenantBase.metadata]

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """Get database URL from environment or config."""
    return os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    
    This function handles both public schema migrations
    and can be extended for tenant-specific migrations.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Set search path to public schema for base migrations
        connection.execute(text("SET search_path TO public"))
        
        context.configure(
            connection=connection,
            target_metadata=Base.metadata,
            include_schemas=True,
            version_table_schema="public"
        )

        with context.begin_transaction():
            context.run_migrations()


def run_tenant_migrations(tenant_id: str) -> None:
    """Run migrations for a specific tenant schema.
    
    Args:
        tenant_id: The tenant identifier to create/migrate schema for
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    schema_name = f"tenant_{tenant_id}"
    
    with connectable.connect() as connection:
        # Create schema if it doesn't exist
        connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        
        # Set search path to tenant schema
        connection.execute(text(f"SET search_path TO {schema_name}, public"))
        
        context.configure(
            connection=connection,
            target_metadata=TenantBase.metadata,
            include_schemas=True,
            version_table_schema=schema_name,
            version_table=f"alembic_version_{tenant_id}"
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Check if we're running tenant-specific migrations
    tenant_id = os.getenv("TENANT_ID")
    if tenant_id:
        run_tenant_migrations(tenant_id)
    else:
        run_migrations_online()
