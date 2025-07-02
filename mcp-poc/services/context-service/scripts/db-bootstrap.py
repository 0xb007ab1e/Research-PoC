#!/usr/bin/env python3
"""
Database Bootstrap Script for MCP Context Service

This script:
1. Connects to PostgreSQL using the configuration settings
2. Creates tenant schemas if missing
3. Runs Alembic migrations per schema
4. Sets up proper permissions and indexes

Usage:
    python scripts/db-bootstrap.py [--tenant-id TENANT_ID]

Environment Variables:
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD - Database connection
    TENANT_IDS - Comma-separated list of tenant IDs to bootstrap (optional)
"""

import os
import sys
import asyncio
import logging
import argparse
from typing import List, Optional
import asyncpg
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from db_models import Context, Base, get_tenant_indexes_sql

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DatabaseBootstrap:
    """Database bootstrap manager for multi-tenant context service"""
    
    def __init__(self):
        self.db_url = settings.get_database_url()
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        
    async def connect_async(self) -> asyncpg.Connection:
        """Create async connection for raw SQL operations"""
        try:
            conn = await asyncpg.connect(
                host=settings.database.db_host,
                port=settings.database.db_port,
                database=settings.database.db_name,
                user=settings.database.db_user,
                password=settings.database.db_password,
                ssl=settings.database.db_ssl_mode if settings.database.db_ssl_mode != 'disable' else False
            )
            logger.info("Successfully connected to PostgreSQL")
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise
    
    def run_migrations(self, schema_name: Optional[str] = None):
        """Run Alembic migrations for the specified schema or public schema"""
        try:
            # Configure Alembic
            alembic_cfg = Config("alembic.ini")
            
            # Set the schema to run migrations in
            if schema_name:
                logger.info(f"Running migrations for schema: {schema_name}")
                # For tenant schemas, we need to set the search path
                alembic_cfg.set_main_option(
                    "sqlalchemy.url", 
                    f"{self.db_url}?options=-csearch_path={schema_name},public"
                )
            else:
                logger.info("Running migrations for public schema")
                alembic_cfg.set_main_option("sqlalchemy.url", self.db_url)
            
            # Run the migration
            command.upgrade(alembic_cfg, "head")
            logger.info(f"Successfully ran migrations for {'schema ' + schema_name if schema_name else 'public schema'}")
            
        except Exception as e:
            logger.error(f"Failed to run migrations for {'schema ' + schema_name if schema_name else 'public schema'}: {e}")
            raise
    
    async def create_tenant_schema(self, tenant_id: str):
        """Create a tenant schema and set up the contexts table"""
        schema_name = f"tenant_{tenant_id}"
        
        try:
            conn = await self.connect_async()
            
            # Validate tenant ID
            if not tenant_id.replace('-', '').replace('_', '').isalnum():
                raise ValueError(f"Invalid tenant ID format: {tenant_id}")
            
            logger.info(f"Creating tenant schema: {schema_name}")
            
            # Use the stored procedure to create the schema
            await conn.execute(f"SELECT create_tenant_schema('{tenant_id}')")
            
            # Create the contexts table in the tenant schema using the Base metadata
            with self.engine.connect() as sql_conn:
                # Set the search path to the tenant schema
                sql_conn.execute(text(f"SET search_path TO {schema_name}, public"))
                
                # Create the table
                Context.__table__.create(sql_conn, checkfirst=True)
                
                # Add indexes
                index_sql = get_tenant_indexes_sql(schema_name)
                for statement in index_sql.split(';'):
                    if statement.strip():
                        sql_conn.execute(text(statement))
                
                sql_conn.commit()
            
            logger.info(f"Successfully created tenant schema: {schema_name}")
            
        except Exception as e:
            logger.error(f"Failed to create tenant schema {schema_name}: {e}")
            raise
        finally:
            if 'conn' in locals():
                await conn.close()
    
    async def verify_schema(self, schema_name: str) -> bool:
        """Verify that a schema exists and has the required tables"""
        try:
            conn = await self.connect_async()
            
            # Check if schema exists
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = $1)",
                schema_name
            )
            
            if not schema_exists:
                return False
            
            # Check if contexts table exists in the schema
            table_exists = await conn.fetchval(
                """
                SELECT EXISTS(
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = $1 AND table_name = 'contexts'
                )
                """,
                schema_name
            )
            
            await conn.close()
            return table_exists
            
        except Exception as e:
            logger.error(f"Failed to verify schema {schema_name}: {e}")
            return False
    
    async def bootstrap_tenant(self, tenant_id: str, force_recreate: bool = False):
        """Bootstrap a single tenant"""
        schema_name = f"tenant_{tenant_id}"
        
        logger.info(f"Bootstrapping tenant: {tenant_id}")
        
        # Check if schema already exists
        schema_exists = await self.verify_schema(schema_name)
        
        if schema_exists and not force_recreate:
            logger.info(f"Schema {schema_name} already exists and is valid")
            return
        
        if schema_exists and force_recreate:
            logger.warning(f"Force recreating schema {schema_name}")
            conn = await self.connect_async()
            await conn.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
            await conn.close()
        
        # Create the tenant schema
        await self.create_tenant_schema(tenant_id)
        
        logger.info(f"Successfully bootstrapped tenant: {tenant_id}")
    
    async def bootstrap_database(self, tenant_ids: Optional[List[str]] = None, force_recreate: bool = False):
        """Bootstrap the entire database"""
        logger.info("Starting database bootstrap process")
        
        try:
            # First, run migrations on the public schema to create core functions
            logger.info("Running core schema migrations...")
            self.run_migrations()
            
            # If tenant IDs are provided, bootstrap those tenants
            if tenant_ids:
                for tenant_id in tenant_ids:
                    await self.bootstrap_tenant(tenant_id, force_recreate)
            else:
                # Get tenant IDs from environment variable
                env_tenant_ids = os.getenv('TENANT_IDS', '')
                if env_tenant_ids:
                    tenant_list = [tid.strip() for tid in env_tenant_ids.split(',') if tid.strip()]
                    for tenant_id in tenant_list:
                        await self.bootstrap_tenant(tenant_id, force_recreate)
                else:
                    logger.info("No tenant IDs specified. Creating default 'default' tenant.")
                    await self.bootstrap_tenant('default', force_recreate)
            
            logger.info("Database bootstrap completed successfully")
            
        except Exception as e:
            logger.error(f"Database bootstrap failed: {e}")
            raise
    
    async def health_check(self) -> bool:
        """Perform a health check on the database"""
        try:
            conn = await self.connect_async()
            
            # Test basic connectivity
            result = await conn.fetchval("SELECT 1")
            
            # Check if core functions exist
            functions_exist = await conn.fetchval(
                """
                SELECT COUNT(*) FROM information_schema.routines 
                WHERE routine_schema = 'public' 
                AND routine_name IN ('create_tenant_schema', 'cleanup_expired_contexts', 'update_updated_at_column')
                """
            )
            
            await conn.close()
            
            if result == 1 and functions_exist == 3:
                logger.info("Database health check passed")
                return True
            else:
                logger.error("Database health check failed - missing core functions")
                return False
                
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


async def main():
    """Main entry point for the bootstrap script"""
    parser = argparse.ArgumentParser(description='Bootstrap Context Service Database')
    parser.add_argument('--tenant-id', type=str, help='Specific tenant ID to bootstrap')
    parser.add_argument('--tenant-ids', type=str, help='Comma-separated list of tenant IDs to bootstrap')
    parser.add_argument('--force-recreate', action='store_true', help='Force recreate existing schemas')
    parser.add_argument('--health-check', action='store_true', help='Perform health check only')
    
    args = parser.parse_args()
    
    bootstrap = DatabaseBootstrap()
    
    try:
        if args.health_check:
            success = await bootstrap.health_check()
            sys.exit(0 if success else 1)
        
        tenant_ids = None
        if args.tenant_id:
            tenant_ids = [args.tenant_id]
        elif args.tenant_ids:
            tenant_ids = [tid.strip() for tid in args.tenant_ids.split(',') if tid.strip()]
        
        await bootstrap.bootstrap_database(tenant_ids, args.force_recreate)
        
    except Exception as e:
        logger.error(f"Bootstrap script failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
