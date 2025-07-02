"""
Tests for repository and database layer with tenant isolation.

Tests cover:
- Basic CRUD operations
- Tenant isolation at the database level
- Error handling
- Connection management
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import asyncpg

from repository import ContextRepository, TenantAwareDB, DatabaseError


class TestTenantAwareDB:
    """Test cases for TenantAwareDB class"""
    
    def test_tenant_aware_db_initialization(self):
        """Test TenantAwareDB initialization"""
        db = TenantAwareDB()
        assert db.database_url is not None

    @pytest.mark.asyncio
    async def test_valid_tenant_id(self):
        """Test setting search path with valid tenant ID"""
        db = TenantAwareDB()
        mock_conn = AsyncMock()
        
        await db.set_search_path(mock_conn, "tenant-123")
        
        mock_conn.execute.assert_called_once_with("SET search_path TO tenant_tenant-123, public")

    @pytest.mark.asyncio
    async def test_invalid_tenant_id(self):
        """Test setting search path with invalid tenant ID"""
        db = TenantAwareDB()
        mock_conn = AsyncMock()
        
        invalid_tenant_ids = [
            "",  # Empty
            None,  # None
            "tenant@invalid",  # Special characters
            "tenant with spaces",  # Spaces
            "tenant/slash",  # Slashes
        ]
        
        for invalid_id in invalid_tenant_ids:
            with pytest.raises(ValueError, match="Invalid tenant ID"):
                await db.set_search_path(mock_conn, invalid_id)

    @pytest.mark.asyncio
    async def test_get_connection_success(self):
        """Test successful database connection"""
        db = TenantAwareDB()
        
        with patch('asyncpg.connect') as mock_connect:
            mock_conn = AsyncMock()
            mock_connect.return_value = mock_conn
            
            async with db.get_connection("tenant-123") as conn:
                assert conn == mock_conn
                mock_conn.execute.assert_called_once_with("SET search_path TO tenant_tenant-123, public")
            
            mock_conn.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_connection_database_error(self):
        """Test database connection error handling"""
        db = TenantAwareDB()
        
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = asyncpg.PostgresError("Connection failed")
            
            with pytest.raises(DatabaseError, match="Database connection failed"):
                async with db.get_connection("tenant-123"):
                    pass

    @pytest.mark.asyncio
    async def test_get_connection_unexpected_error(self):
        """Test unexpected error during connection"""
        db = TenantAwareDB()
        
        with patch('asyncpg.connect') as mock_connect:
            mock_connect.side_effect = Exception("Unexpected error")
            
            with pytest.raises(DatabaseError, match="Unexpected database error"):
                async with db.get_connection("tenant-123"):
                    pass


class TestContextRepository:
    """Test cases for ContextRepository class"""
    
    @pytest.fixture
    def repository(self):
        """Create a ContextRepository instance for testing"""
        return ContextRepository()

    @pytest.fixture
    def sample_context_data(self):
        """Sample context data for testing"""
        return {
            'context_data': {'key': 'value', 'nested': {'data': 'test'}},
            'context_type': 'test_type',
            'title': 'Test Context',
            'description': 'Test description',
            'tags': ['tag1', 'tag2'],
            'user_id': 'user-123',
            'expires_at': None
        }

    @pytest.mark.asyncio
    async def test_create_context_success(self, repository, sample_context_data):
        """Test successful context creation"""
        tenant_id = "tenant-123"
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            # Mock successful database insert
            mock_conn.fetchrow.return_value = {'id': 'ctx_generated-id'}
            
            context_id = await repository.create_context(tenant_id, sample_context_data)
            
            assert context_id == 'ctx_generated-id'
            mock_conn.fetchrow.assert_called_once()
            
            # Verify the query was called with correct parameters
            call_args = mock_conn.fetchrow.call_args
            assert "INSERT INTO contexts" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_create_context_unique_violation(self, repository, sample_context_data):
        """Test context creation with ID conflict"""
        tenant_id = "tenant-123"
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            # Mock unique violation error
            mock_conn.fetchrow.side_effect = asyncpg.UniqueViolationError("Duplicate key")
            
            with pytest.raises(DatabaseError, match="Context with this ID already exists"):
                await repository.create_context(tenant_id, sample_context_data)

    @pytest.mark.asyncio
    async def test_get_context_success(self, repository):
        """Test successful context retrieval"""
        tenant_id = "tenant-123"
        context_id = "ctx_test-id"
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            # Mock successful database query
            mock_conn.fetchrow.return_value = {
                'id': context_id,
                'context_data': '{"key": "value"}',
                'context_type': 'test',
                'title': 'Test',
                'description': 'Test desc',
                'tags': ['tag1'],
                'tenant_id': tenant_id,
                'user_id': 'user-123',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'expires_at': None,
                'version': 1
            }
            
            result = await repository.get_context(tenant_id, context_id)
            
            assert result is not None
            assert result['id'] == context_id
            assert result['context_data'] == {"key": "value"}  # Should be parsed from JSON
            mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_context_not_found(self, repository):
        """Test context retrieval when context doesn't exist"""
        tenant_id = "tenant-123"
        context_id = "ctx_nonexistent"
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            # Mock no result found
            mock_conn.fetchrow.return_value = None
            
            result = await repository.get_context(tenant_id, context_id)
            
            assert result is None
            mock_conn.fetchrow.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_context_success(self, repository):
        """Test successful context update"""
        tenant_id = "tenant-123"
        context_id = "ctx_test-id"
        update_data = {
            'title': 'Updated Title',
            'description': 'Updated Description'
        }
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            # Mock successful update (1 row affected)
            mock_conn.execute.return_value = "UPDATE 1"
            
            result = await repository.update_context(tenant_id, context_id, update_data)
            
            assert result is True
            mock_conn.execute.assert_called_once()
            
            # Verify the query was called with correct parameters
            call_args = mock_conn.execute.call_args
            assert "UPDATE contexts" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_update_context_not_found(self, repository):
        """Test context update when context doesn't exist"""
        tenant_id = "tenant-123"
        context_id = "ctx_nonexistent"
        update_data = {'title': 'Updated Title'}
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            # Mock no rows affected
            mock_conn.execute.return_value = "UPDATE 0"
            
            result = await repository.update_context(tenant_id, context_id, update_data)
            
            assert result is False
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_context_success(self, repository):
        """Test successful context deletion"""
        tenant_id = "tenant-123"
        context_id = "ctx_test-id"
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            # Mock successful deletion (1 row affected)
            mock_conn.execute.return_value = "DELETE 1"
            
            result = await repository.delete_context(tenant_id, context_id)
            
            assert result is True
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_context_not_found(self, repository):
        """Test context deletion when context doesn't exist"""
        tenant_id = "tenant-123"
        context_id = "ctx_nonexistent"
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            # Mock no rows affected
            mock_conn.execute.return_value = "DELETE 0"
            
            result = await repository.delete_context(tenant_id, context_id)
            
            assert result is False
            mock_conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_tenant_isolation_in_queries(self, repository):
        """Test that tenant isolation is properly enforced in database queries"""
        tenant_a = "tenant-a"
        tenant_b = "tenant-b"
        context_id = "ctx_shared-id"
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn_a = AsyncMock()
            mock_conn_b = AsyncMock()
            
            # Setup different connections for different tenants
            def get_connection_side_effect(tenant_id):
                if tenant_id == tenant_a:
                    mock_conn_a.__aenter__.return_value = mock_conn_a
                    mock_conn_a.__aexit__.return_value = None
                    return mock_conn_a
                else:
                    mock_conn_b.__aenter__.return_value = mock_conn_b
                    mock_conn_b.__aexit__.return_value = None
                    return mock_conn_b
            
            mock_get_conn.side_effect = get_connection_side_effect
            
            # Tenant A can see the context
            mock_conn_a.fetchrow.return_value = {'id': context_id, 'context_data': '{}', 'tenant_id': tenant_a}
            result_a = await repository.get_context(tenant_a, context_id)
            assert result_a is not None
            
            # Tenant B cannot see the same context (due to schema isolation)
            mock_conn_b.fetchrow.return_value = None
            result_b = await repository.get_context(tenant_b, context_id)
            assert result_b is None
            
            # Verify that different connections were used
            assert mock_conn_a.fetchrow.called
            assert mock_conn_b.fetchrow.called

    @pytest.mark.asyncio
    async def test_database_error_handling(self, repository, sample_context_data):
        """Test general database error handling"""
        tenant_id = "tenant-123"
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            # Mock database error
            mock_conn.fetchrow.side_effect = Exception("Database error")
            
            with pytest.raises(DatabaseError, match="Failed to create context"):
                await repository.create_context(tenant_id, sample_context_data)

    @pytest.mark.asyncio
    async def test_json_serialization_handling(self, repository):
        """Test proper JSON serialization/deserialization"""
        tenant_id = "tenant-123"
        context_id = "ctx_test-id"
        
        # Complex nested data structure
        complex_data = {
            'arrays': [1, 2, 3],
            'nested': {'deep': {'value': 'test'}},
            'unicode': 'Hello 世界',
            'null_value': None,
            'boolean': True
        }
        
        with patch.object(repository.db, 'get_connection') as mock_get_conn:
            mock_conn = AsyncMock()
            mock_conn.__aenter__.return_value = mock_conn
            mock_conn.__aexit__.return_value = None
            mock_get_conn.return_value = mock_conn
            
            import json
            # Mock successful database query with JSON data
            mock_conn.fetchrow.return_value = {
                'id': context_id,
                'context_data': json.dumps(complex_data),
                'context_type': 'test',
                'title': 'Test',
                'description': 'Test desc',
                'tags': ['tag1'],
                'tenant_id': tenant_id,
                'user_id': 'user-123',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow(),
                'expires_at': None,
                'version': 1
            }
            
            result = await repository.get_context(tenant_id, context_id)
            
            assert result is not None
            assert result['context_data'] == complex_data  # Should be properly deserialized
