"""
Pydantic models for the MCP Context Service
Defines request/response schemas with validation and security considerations
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, validator
from datetime import datetime
import uuid

class ContextCreateRequest(BaseModel):
    """Request model for creating context data"""
    
    # Required fields
    context_data: Dict[str, Any] = Field(
        ...,
        description="The context data to store (JSON object)"
    )
    
    context_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type/category of the context (e.g., 'user_preferences', 'session_data')"
    )
    
    # Optional fields with defaults
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Human-readable title for the context"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Description of the context data"
    )
    
    tags: Optional[List[str]] = Field(
        default_factory=list,
        description="Tags for categorizing and searching context"
    )
    
    # Metadata
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiration timestamp for the context"
    )
    
    # Tenant and user context
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier for multi-tenant environments"
    )
    
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier for audit and tracking"
    )
    
    # Request metadata
    request_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this request"
    )
    
    @validator('context_data')
    def validate_context_data(cls, v):
        """Validate context data for security and size"""
        
        # Check data size (prevent huge payloads)
        import json
        data_size = len(json.dumps(v))
        if data_size > 1024 * 1024:  # 1MB limit
            raise ValueError('Context data too large (max 1MB)')
        
        # Basic security check for potentially malicious content
        data_str = json.dumps(v).lower()
        suspicious_patterns = ['<script', 'javascript:', 'data:', 'vbscript:', 'eval(']
        for pattern in suspicious_patterns:
            if pattern in data_str:
                raise ValueError('Context data contains potentially malicious content')
        
        return v
    
    @validator('context_type')
    def validate_context_type(cls, v):
        """Validate context type"""
        # Allow alphanumeric, underscores, hyphens, dots
        if not all(c.isalnum() or c in '-_.' for c in v):
            raise ValueError('Context type can only contain alphanumeric characters, hyphens, underscores, and dots')
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags"""
        if v and len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        
        for tag in v:
            if not isinstance(tag, str) or len(tag) > 50:
                raise ValueError('Each tag must be a string with max 50 characters')
            
            # Basic validation for tag content
            if not all(c.isalnum() or c in '-_.' for c in tag):
                raise ValueError('Tags can only contain alphanumeric characters, hyphens, underscores, and dots')
        
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "context_data": {
                    "user_preferences": {
                        "theme": "dark",
                        "language": "en",
                        "notifications": True
                    },
                    "last_activity": "2024-01-15T10:30:00Z"
                },
                "context_type": "user_preferences",
                "title": "User UI Preferences",
                "description": "User interface preferences and settings",
                "tags": ["ui", "preferences", "settings"],
                "tenant_id": "tenant-123",
                "user_id": "user-456"
            }
        }

class ContextUpdateRequest(BaseModel):
    """Request model for updating context data"""
    
    # Optional fields for partial updates
    context_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Updated context data (JSON object)"
    )
    
    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Updated title for the context"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Updated description of the context data"
    )
    
    tags: Optional[List[str]] = Field(
        default=None,
        description="Updated tags for categorizing and searching context"
    )
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Updated expiration timestamp for the context"
    )
    
    # Request metadata
    request_id: Optional[str] = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique identifier for this request"
    )
    
    @validator('context_data')
    def validate_context_data(cls, v):
        """Validate context data for security and size"""
        if v is None:
            return v
            
        # Check data size (prevent huge payloads)
        import json
        data_size = len(json.dumps(v))
        if data_size > 1024 * 1024:  # 1MB limit
            raise ValueError('Context data too large (max 1MB)')
        
        # Basic security check for potentially malicious content
        data_str = json.dumps(v).lower()
        suspicious_patterns = ['<script', 'javascript:', 'data:', 'vbscript:', 'eval(']
        for pattern in suspicious_patterns:
            if pattern in data_str:
                raise ValueError('Context data contains potentially malicious content')
        
        return v
    
    @validator('tags')
    def validate_tags(cls, v):
        """Validate tags"""
        if v is None:
            return v
            
        if len(v) > 20:
            raise ValueError('Maximum 20 tags allowed')
        
        for tag in v:
            if not isinstance(tag, str) or len(tag) > 50:
                raise ValueError('Each tag must be a string with max 50 characters')
            
            # Basic validation for tag content
            if not all(c.isalnum() or c in '-_.' for c in tag):
                raise ValueError('Tags can only contain alphanumeric characters, hyphens, underscores, and dots')
        
        return v

class ContextResponse(BaseModel):
    """Response model for context data"""
    
    # Core response data
    id: str = Field(
        ...,
        description="Unique identifier for the context"
    )
    
    context_data: Dict[str, Any] = Field(
        ...,
        description="The stored context data"
    )
    
    context_type: str = Field(
        ...,
        description="Type/category of the context"
    )
    
    title: Optional[str] = Field(
        default=None,
        description="Human-readable title for the context"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Description of the context data"
    )
    
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorizing and searching context"
    )
    
    # Metadata
    tenant_id: Optional[str] = Field(
        default=None,
        description="Tenant identifier"
    )
    
    user_id: Optional[str] = Field(
        default=None,
        description="User identifier who created/owns the context"
    )
    
    created_at: datetime = Field(
        ...,
        description="Context creation timestamp"
    )
    
    updated_at: datetime = Field(
        ...,
        description="Context last update timestamp"
    )
    
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Context expiration timestamp"
    )
    
    # Versioning
    version: int = Field(
        default=1,
        description="Version number for optimistic locking"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "id": "ctx_123e4567-e89b-12d3-a456-426614174000",
                "context_data": {
                    "user_preferences": {
                        "theme": "dark",
                        "language": "en",
                        "notifications": True
                    },
                    "last_activity": "2024-01-15T10:30:00Z"
                },
                "context_type": "user_preferences",
                "title": "User UI Preferences",
                "description": "User interface preferences and settings",
                "tags": ["ui", "preferences", "settings"],
                "tenant_id": "tenant-123",
                "user_id": "user-456",
                "created_at": "2024-01-15T08:00:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "expires_at": null,
                "version": 1
            }
        }

class ErrorResponse(BaseModel):
    """Standard error response model"""
    
    error_code: str = Field(
        ...,
        description="Specific error code for programmatic handling"
    )
    
    error_message: str = Field(
        ...,
        description="Human-readable error message"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Request ID if available"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Error timestamp"
    )
    
    class Config:
        schema_extra = {
            "example": {
                "error_code": "CONTEXT_NOT_FOUND",
                "error_message": "Context with the specified ID was not found",
                "request_id": "123e4567-e89b-12d3-a456-426614174000",
                "details": {
                    "context_id": "ctx_missing-id",
                    "tenant_id": "tenant-123"
                }
            }
        }

class HealthCheckResponse(BaseModel):
    """Health check response model"""
    
    status: str = Field(
        ...,
        description="Service health status"
    )
    
    version: str = Field(
        ...,
        description="Service version"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Health check timestamp"
    )
    
    dependencies: Dict[str, str] = Field(
        default_factory=dict,
        description="Status of external dependencies"
    )
    
    uptime_seconds: Optional[int] = Field(
        default=None,
        description="Service uptime in seconds"
    )

class MetricsResponse(BaseModel):
    """Service metrics response model"""
    
    total_contexts: int = Field(
        default=0,
        description="Total number of contexts stored"
    )
    
    contexts_by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of contexts by type"
    )
    
    total_requests: int = Field(
        default=0,
        description="Total number of requests processed"
    )
    
    successful_requests: int = Field(
        default=0,
        description="Number of successful requests"
    )
    
    failed_requests: int = Field(
        default=0,
        description="Number of failed requests"
    )
    
    average_response_time_ms: float = Field(
        default=0.0,
        description="Average response time in milliseconds"
    )
    
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metrics timestamp"
    )
