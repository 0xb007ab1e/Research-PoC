"""
Repository layer for the Context Service using a tenant-aware PostgreSQL database.
Implements secure tenant isolation using schema-based separation.
"""

from typing import Dict, Any, Optional, List
import asyncpg
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
import structlog

from config import settings

logger = structlog.get_logger(__name__)

class DatabaseError(Exception):
    """Raised when database operations fail"""
    pass

class TenantAwareDB:
    """Tenant-aware database connection manager with schema isolation"""
    
    def __init__(self):
        self.database_url = settings.get_database_url()
    
    async def set_search_path(self, conn, tenant_id: str):
        """Set the search path for the given tenant ID with validation"""
        # Validate tenant ID to prevent SQL injection
        if not tenant_id or not tenant_id.replace('-', '').replace('_', '').isalnum():
            raise ValueError(f"Invalid tenant ID: {tenant_id}")
        
        # Use parameterized query to set search path safely
        schema_name = f"tenant_{tenant_id}"
        await conn.execute(f"SET search_path TO {schema_name}, public")
        
        logger.debug(f"Set search path to {schema_name}")
    
    @asynccontextmanager
    async def get_connection(self, tenant_id: str):
        """Provide a tenant-scoped database connection with error handling"""
        conn = None
        try:
            conn = await asyncpg.connect(
                self.database_url,
                timeout=settings.database.db_timeout
            )
            await self.set_search_path(conn, tenant_id)
            yield conn
        except asyncpg.PostgresError as e:
            logger.error(f"Database connection error for tenant {tenant_id}: {e}")
            raise DatabaseError(f"Database connection failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error for tenant {tenant_id}: {e}")
            raise DatabaseError(f"Unexpected database error: {e}")
        finally:
            if conn:
                await conn.close()


class ContextRepository:
    """Repository for managing context data with tenant isolation"""
    
    def __init__(self):
        self.db = TenantAwareDB()
    
    async def create_context(self, tenant_id: str, context_data: Dict[str, Any]) -> str:
        """Create a new context entry"""
        try:
            context_id = f"ctx_{uuid.uuid4()}"
            
            async with self.db.get_connection(tenant_id) as conn:
                result = await conn.fetchrow(
                    """
                    INSERT INTO contexts (
                        id, context_data, context_type, title, description, 
                        tags, tenant_id, user_id, created_at, updated_at, 
                        expires_at, version
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, NOW(), NOW(), $9, 1)
                    RETURNING id
                    """,
                    context_id,
                    json.dumps(context_data['context_data']),
                    context_data['context_type'],
                    context_data.get('title'),
                    context_data.get('description'),
                    context_data.get('tags', []),
                    tenant_id,
                    context_data.get('user_id'),
                    datetime.utcnow(),
                    context_data.get('expires_at')
                )
                
                logger.info(
                    "Context created successfully",
                    context_id=context_id,
                    tenant_id=tenant_id,
                    context_type=context_data['context_type']
                )
                
                return result['id']
                
        except asyncpg.UniqueViolationError as e:
            logger.error(f"Context ID conflict: {e}")
            raise DatabaseError("Context with this ID already exists")
        except Exception as e:
            logger.error(f"Failed to create context: {e}")
            raise DatabaseError(f"Failed to create context: {e}")
    
    async def get_context(self, tenant_id: str, context_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a context by ID"""
        try:
            async with self.db.get_connection(tenant_id) as conn:
                result = await conn.fetchrow(
                    """
                    SELECT id, context_data, context_type, title, description, 
                           tags, tenant_id, user_id, created_at, updated_at, 
                           expires_at, version
                    FROM contexts 
                    WHERE id = $1 AND (expires_at IS NULL OR expires_at > NOW())
                    """,
                    context_id
                )
                
                if result:
                    context_dict = dict(result)
                    # Parse JSON context_data
                    if context_dict['context_data']:
                        context_dict['context_data'] = json.loads(context_dict['context_data'])
                    
                    logger.debug(
                        "Context retrieved successfully",
                        context_id=context_id,
                        tenant_id=tenant_id
                    )
                    
                    return context_dict
                else:
                    logger.debug(
                        "Context not found or expired",
                        context_id=context_id,
                        tenant_id=tenant_id
                    )
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to retrieve context {context_id}: {e}")
            raise DatabaseError(f"Failed to retrieve context: {e}")
    
    async def update_context(self, tenant_id: str, context_id: str, update_data: Dict[str, Any]) -> bool:
        """Update an existing context"""
        try:
            async with self.db.get_connection(tenant_id) as conn:
                # Prepare update fields
                context_data_json = None
                if 'context_data' in update_data and update_data['context_data'] is not None:
                    context_data_json = json.dumps(update_data['context_data'])
                
                result = await conn.execute(
                    """
                    UPDATE contexts
                    SET context_data = COALESCE($2, context_data),
                        title = COALESCE($3, title),
                        description = COALESCE($4, description),
                        tags = COALESCE($5, tags),
                        updated_at = NOW(),
                        expires_at = COALESCE($6, expires_at),
                        version = version + 1
                    WHERE id = $1 AND (expires_at IS NULL OR expires_at > NOW())
                    """,
                    context_id,
                    context_data_json,
                    update_data.get('title'),
                    update_data.get('description'),
                    update_data.get('tags'),
                    update_data.get('expires_at')
                )
                
                # Check if any rows were affected
                rows_affected = int(result.split()[-1]) if result else 0
                
                if rows_affected > 0:
                    logger.info(
                        "Context updated successfully",
                        context_id=context_id,
                        tenant_id=tenant_id
                    )
                    return True
                else:
                    logger.warning(
                        "Context not found or expired for update",
                        context_id=context_id,
                        tenant_id=tenant_id
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to update context {context_id}: {e}")
            raise DatabaseError(f"Failed to update context: {e}")
    
    async def delete_context(self, tenant_id: str, context_id: str) -> bool:
        """Delete a context (soft delete by setting expires_at)"""
        try:
            async with self.db.get_connection(tenant_id) as conn:
                result = await conn.execute(
                    """
                    UPDATE contexts
                    SET expires_at = NOW(),
                        updated_at = NOW()
                    WHERE id = $1 AND (expires_at IS NULL OR expires_at > NOW())
                    """,
                    context_id
                )
                
                rows_affected = int(result.split()[-1]) if result else 0
                
                if rows_affected > 0:
                    logger.info(
                        "Context deleted successfully",
                        context_id=context_id,
                        tenant_id=tenant_id
                    )
                    return True
                else:
                    logger.warning(
                        "Context not found for deletion",
                        context_id=context_id,
                        tenant_id=tenant_id
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete context {context_id}: {e}")
            raise DatabaseError(f"Failed to delete context: {e}")
    
    async def list_contexts(
        self, 
        tenant_id: str, 
        context_type: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List contexts with optional filtering"""
        try:
            query = """
                SELECT id, context_data, context_type, title, description, 
                       tags, tenant_id, user_id, created_at, updated_at, 
                       expires_at, version
                FROM contexts 
                WHERE (expires_at IS NULL OR expires_at > NOW())
            """
            
            params = []
            param_count = 0
            
            if context_type:
                param_count += 1
                query += f" AND context_type = ${param_count}"
                params.append(context_type)
            
            if user_id:
                param_count += 1
                query += f" AND user_id = ${param_count}"
                params.append(user_id)
            
            query += " ORDER BY created_at DESC"
            
            param_count += 1
            query += f" LIMIT ${param_count}"
            params.append(limit)
            
            param_count += 1
            query += f" OFFSET ${param_count}"
            params.append(offset)
            
            async with self.db.get_connection(tenant_id) as conn:
                results = await conn.fetch(query, *params)
                
                contexts = []
                for result in results:
                    context_dict = dict(result)
                    # Parse JSON context_data
                    if context_dict['context_data']:
                        context_dict['context_data'] = json.loads(context_dict['context_data'])
                    contexts.append(context_dict)
                
                logger.debug(
                    "Contexts listed successfully",
                    tenant_id=tenant_id,
                    count=len(contexts),
                    context_type=context_type,
                    user_id=user_id
                )
                
                return contexts
                
        except Exception as e:
            logger.error(f"Failed to list contexts: {e}")
            raise DatabaseError(f"Failed to list contexts: {e}")
    
    async def cleanup_expired_contexts(self, tenant_id: str) -> int:
        """Clean up expired contexts (hard delete)"""
        try:
            async with self.db.get_connection(tenant_id) as conn:
                result = await conn.execute(
                    "DELETE FROM contexts WHERE expires_at IS NOT NULL AND expires_at <= NOW()"
                )
                
                rows_deleted = int(result.split()[-1]) if result else 0
                
                if rows_deleted > 0:
                    logger.info(
                        "Expired contexts cleaned up",
                        tenant_id=tenant_id,
                        deleted_count=rows_deleted
                    )
                
                return rows_deleted
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired contexts: {e}")
            raise DatabaseError(f"Failed to cleanup contexts: {e}")

