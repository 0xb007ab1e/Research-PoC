"""
Unit tests for Pydantic models and validators in context-service.

Tests cover:
- Model validation
- Validator logic
- Edge cases and error conditions
- Security validation
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
import json

from models import (
    ContextCreateRequest,
    ContextUpdateRequest,
    ContextResponse,
    ErrorResponse,
    HealthCheckResponse,
    MetricsResponse
)


class TestContextCreateRequest:
    """Test cases for ContextCreateRequest model"""

    def test_valid_context_create_request(self):
        """Test creation of valid context request"""
        request = ContextCreateRequest(
            context_data={"user_id": "123", "preferences": {"theme": "dark"}},
            context_type="user_preferences",
            title="User Settings",
            description="User UI preferences",
            tags=["ui", "preferences"],
            tenant_id="tenant-1",
            user_id="user-123"
        )
        
        assert request.context_data == {"user_id": "123", "preferences": {"theme": "dark"}}
        assert request.context_type == "user_preferences"
        assert request.title == "User Settings"
        assert request.description == "User UI preferences"
        assert request.tags == ["ui", "preferences"]
        assert request.tenant_id == "tenant-1"
        assert request.user_id == "user-123"
        assert request.request_id is not None

    def test_minimal_valid_request(self):
        """Test minimal valid context request"""
        request = ContextCreateRequest(
            context_data={"test": "data"},
            context_type="test"
        )
        
        assert request.context_data == {"test": "data"}
        assert request.context_type == "test"
        assert request.title is None
        assert request.description is None
        assert request.tags == []
        assert request.expires_at is None

    def test_context_type_validation(self):
        """Test context_type validation"""
        # Valid context types
        valid_types = [
            "user_preferences",
            "session-data",
            "config.settings",
            "test123",
            "a_b-c.d"
        ]
        
        for context_type in valid_types:
            request = ContextCreateRequest(
                context_data={"test": "data"},
                context_type=context_type
            )
            assert request.context_type == context_type

    def test_invalid_context_type(self):
        """Test invalid context_type values"""
        invalid_types = [
            "",  # Empty string
            "invalid@type",  # Special characters
            "type with spaces",  # Spaces
            "type/with/slashes",  # Slashes
            "type#with#hash",  # Hash symbols
        ]
        
        for context_type in invalid_types:
            with pytest.raises(ValidationError) as exc_info:
                ContextCreateRequest(
                    context_data={"test": "data"},
                    context_type=context_type
                )
            assert "Context type can only contain" in str(exc_info.value)

    def test_context_data_size_limit(self):
        """Test context_data size validation"""
        # Create data that exceeds 1MB limit
        large_data = {"data": "x" * (1024 * 1024 + 1)}
        
        with pytest.raises(ValidationError) as exc_info:
            ContextCreateRequest(
                context_data=large_data,
                context_type="test"
            )
        assert "Context data too large" in str(exc_info.value)

    def test_malicious_content_detection(self):
        """Test security validation for malicious content"""
        malicious_data_cases = [
            {"script": "<script>alert('xss')</script>"},
            {"js": "javascript:alert('xss')"},
            {"data_uri": "data:text/html,<script>alert('xss')</script>"},
            {"vbs": "vbscript:msgbox('xss')"},
            {"eval": "eval('malicious code')"}
        ]
        
        for malicious_data in malicious_data_cases:
            with pytest.raises(ValidationError) as exc_info:
                ContextCreateRequest(
                    context_data=malicious_data,
                    context_type="test"
                )
            assert "potentially malicious content" in str(exc_info.value)

    def test_tags_validation(self):
        """Test tags validation"""
        # Valid tags
        valid_tags = ["tag1", "tag-2", "tag_3", "tag.4"]
        request = ContextCreateRequest(
            context_data={"test": "data"},
            context_type="test",
            tags=valid_tags
        )
        assert request.tags == valid_tags

    def test_too_many_tags(self):
        """Test validation for too many tags"""
        too_many_tags = [f"tag{i}" for i in range(21)]  # 21 tags
        
        with pytest.raises(ValidationError) as exc_info:
            ContextCreateRequest(
                context_data={"test": "data"},
                context_type="test",
                tags=too_many_tags
            )
        assert "Maximum 20 tags allowed" in str(exc_info.value)

    def test_invalid_tag_content(self):
        """Test validation for invalid tag content"""
        invalid_tags = [
            ["tag with spaces"],
            ["tag@symbol"],
            ["tag/slash"],
            ["x" * 51],  # Too long
            [123],  # Not a string
        ]
        
        for tags in invalid_tags:
            with pytest.raises(ValidationError):
                ContextCreateRequest(
                    context_data={"test": "data"},
                    context_type="test",
                    tags=tags
                )

    def test_expires_at_validation(self):
        """Test expires_at field"""
        future_date = datetime.utcnow() + timedelta(days=1)
        request = ContextCreateRequest(
            context_data={"test": "data"},
            context_type="test",
            expires_at=future_date
        )
        assert request.expires_at == future_date


class TestContextUpdateRequest:
    """Test cases for ContextUpdateRequest model"""

    def test_valid_update_request(self):
        """Test valid update request"""
        request = ContextUpdateRequest(
            context_data={"updated": "data"},
            title="Updated Title",
            description="Updated Description",
            tags=["updated", "tags"]
        )
        
        assert request.context_data == {"updated": "data"}
        assert request.title == "Updated Title"
        assert request.description == "Updated Description"
        assert request.tags == ["updated", "tags"]

    def test_partial_update_request(self):
        """Test partial update with only some fields"""
        request = ContextUpdateRequest(
            title="Only Title Updated"
        )
        
        assert request.context_data is None
        assert request.title == "Only Title Updated"
        assert request.description is None
        assert request.tags is None

    def test_empty_update_request(self):
        """Test empty update request"""
        request = ContextUpdateRequest()
        
        assert request.context_data is None
        assert request.title is None
        assert request.description is None
        assert request.tags is None
        assert request.expires_at is None

    def test_update_context_data_validation(self):
        """Test context_data validation in update request"""
        # Test size limit
        large_data = {"data": "x" * (1024 * 1024 + 1)}
        
        with pytest.raises(ValidationError) as exc_info:
            ContextUpdateRequest(context_data=large_data)
        assert "Context data too large" in str(exc_info.value)

    def test_update_malicious_content_detection(self):
        """Test security validation in update request"""
        malicious_data = {"script": "<script>alert('xss')</script>"}
        
        with pytest.raises(ValidationError) as exc_info:
            ContextUpdateRequest(context_data=malicious_data)
        assert "potentially malicious content" in str(exc_info.value)


class TestContextResponse:
    """Test cases for ContextResponse model"""

    def test_valid_context_response(self):
        """Test valid context response creation"""
        now = datetime.utcnow()
        response = ContextResponse(
            id="ctx_123",
            context_data={"test": "data"},
            context_type="test",
            title="Test Context",
            description="Test Description",
            tags=["test"],
            tenant_id="tenant-1",
            user_id="user-123",
            created_at=now,
            updated_at=now,
            version=1
        )
        
        assert response.id == "ctx_123"
        assert response.context_data == {"test": "data"}
        assert response.context_type == "test"
        assert response.title == "Test Context"
        assert response.description == "Test Description"
        assert response.tags == ["test"]
        assert response.tenant_id == "tenant-1"
        assert response.user_id == "user-123"
        assert response.created_at == now
        assert response.updated_at == now
        assert response.version == 1


class TestErrorResponse:
    """Test cases for ErrorResponse model"""

    def test_valid_error_response(self):
        """Test valid error response creation"""
        error = ErrorResponse(
            error_code="CONTEXT_NOT_FOUND",
            error_message="Context with specified ID not found",
            request_id="req-123",
            details={"context_id": "ctx-missing"}
        )
        
        assert error.error_code == "CONTEXT_NOT_FOUND"
        assert error.error_message == "Context with specified ID not found"
        assert error.request_id == "req-123"
        assert error.details == {"context_id": "ctx-missing"}
        assert error.timestamp is not None

    def test_minimal_error_response(self):
        """Test minimal error response"""
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message="An internal error occurred"
        )
        
        assert error.error_code == "INTERNAL_ERROR"
        assert error.error_message == "An internal error occurred"
        assert error.request_id is None
        assert error.details is None
        assert error.timestamp is not None


class TestHealthCheckResponse:
    """Test cases for HealthCheckResponse model"""

    def test_valid_health_response(self):
        """Test valid health check response"""
        health = HealthCheckResponse(
            status="healthy",
            version="1.0.0",
            dependencies={"database": "healthy", "redis": "healthy"},
            uptime_seconds=3600
        )
        
        assert health.status == "healthy"
        assert health.version == "1.0.0"
        assert health.dependencies == {"database": "healthy", "redis": "healthy"}
        assert health.uptime_seconds == 3600
        assert health.timestamp is not None


class TestMetricsResponse:
    """Test cases for MetricsResponse model"""

    def test_valid_metrics_response(self):
        """Test valid metrics response"""
        metrics = MetricsResponse(
            total_contexts=100,
            contexts_by_type={"user_preferences": 50, "session_data": 30, "config": 20},
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            average_response_time_ms=125.5
        )
        
        assert metrics.total_contexts == 100
        assert metrics.contexts_by_type == {"user_preferences": 50, "session_data": 30, "config": 20}
        assert metrics.total_requests == 1000
        assert metrics.successful_requests == 950
        assert metrics.failed_requests == 50
        assert metrics.average_response_time_ms == 125.5
        assert metrics.timestamp is not None

    def test_default_metrics_response(self):
        """Test metrics response with default values"""
        metrics = MetricsResponse()
        
        assert metrics.total_contexts == 0
        assert metrics.contexts_by_type == {}
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
        assert metrics.average_response_time_ms == 0.0
        assert metrics.timestamp is not None


class TestModelEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_unicode_content(self):
        """Test handling of unicode content"""
        unicode_data = {
            "text": "Hello 世界! 🌍 Ñoël",
            "emoji": "😀🎉🚀",
            "special": "çäöü"
        }
        
        request = ContextCreateRequest(
            context_data=unicode_data,
            context_type="unicode_test"
        )
        
        assert request.context_data == unicode_data

    def test_deeply_nested_data(self):
        """Test deeply nested JSON data"""
        nested_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deep_value"
                        }
                    }
                }
            }
        }
        
        request = ContextCreateRequest(
            context_data=nested_data,
            context_type="nested_test"
        )
        
        assert request.context_data == nested_data

    def test_array_data(self):
        """Test arrays in context data"""
        array_data = {
            "numbers": [1, 2, 3, 4, 5],
            "strings": ["a", "b", "c"],
            "mixed": [1, "two", {"three": 3}, [4, 5]]
        }
        
        request = ContextCreateRequest(
            context_data=array_data,
            context_type="array_test"
        )
        
        assert request.context_data == array_data

    def test_null_values(self):
        """Test handling of null values"""
        null_data = {
            "null_value": None,
            "empty_string": "",
            "empty_list": [],
            "empty_dict": {}
        }
        
        request = ContextCreateRequest(
            context_data=null_data,
            context_type="null_test"
        )
        
        assert request.context_data == null_data

    def test_numeric_precision(self):
        """Test numeric precision handling"""
        numeric_data = {
            "float": 123.456789,
            "large_int": 9223372036854775807,
            "small_float": 0.0000001,
            "negative": -999.999
        }
        
        request = ContextCreateRequest(
            context_data=numeric_data,
            context_type="numeric_test"
        )
        
        assert request.context_data == numeric_data
